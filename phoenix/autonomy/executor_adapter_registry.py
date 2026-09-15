from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class ExecutorAdapterDescriptor:
    adapter_id: str
    status: str
    engine_id: str
    actions: tuple[str,...]
    mutation_capable: bool
    gateway_required: bool
    plan_dispatchable: bool
    implementation: str
    priority: int

    @classmethod
    def from_dict(cls,d:dict[str,Any]) -> "ExecutorAdapterDescriptor":
        return cls(
            adapter_id=str(d["adapter_id"]),
            status=str(d["status"]),
            engine_id=str(d["engine_id"]),
            actions=tuple(str(x) for x in d["actions"]),
            mutation_capable=bool(d["mutation_capable"]),
            gateway_required=bool(d["gateway_required"]),
            plan_dispatchable=bool(d["plan_dispatchable"]),
            implementation=str(d["implementation"]),
            priority=int(d["priority"]),
        )


class UniversalCapabilityExecutorRegistry:
    def __init__(
        self,
        config:dict[str,Any],
        engine_registry:dict[str,Any],
        *,
        host:Any=None,
    ):
        self.config=config
        self.engine_registry=engine_registry
        self.host=host
        self.descriptors=tuple(
            ExecutorAdapterDescriptor.from_dict(x)
            for x in config.get("adapters",())
            if x.get("status")=="ACTIVE"
        )
        self._validate()
        self._instances:dict[str,Any]={}

    @classmethod
    def from_repo(cls,repo_root:Path,*,host:Any=None) -> "UniversalCapabilityExecutorRegistry":
        cfg=Path(repo_root)/"configs/phoenix"
        return cls(
            json.loads((cfg/"capability_executor_registry_v1.json").read_text(encoding="utf-8-sig")),
            json.loads((cfg/"engine_registry_v1.json").read_text(encoding="utf-8-sig")),
            host=host,
        )

    def _active_engines(self) -> dict[str,dict[str,Any]]:
        return {
            str(e["engine_id"]):e
            for e in self.engine_registry.get("engines",())
            if e.get("status")=="ACTIVE"
        }

    def _validate(self) -> None:
        if self.config.get("schema")!="PHOENIX_CAPABILITY_EXECUTOR_REGISTRY_V1":
            raise RuntimeError("executor registry schema invalid")
        if self.config.get("status")!="ACTIVE" or self.config.get("fail_closed") is not True:
            raise RuntimeError("executor registry must be active and fail closed")
        if self.config.get("future_action_default")!="DENY_NO_REGISTERED_ADAPTER":
            raise RuntimeError("executor registry future default must deny")

        engines=self._active_engines()
        ids=set()
        coverage:dict[tuple[str,str],list[ExecutorAdapterDescriptor]]={}
        for d in self.descriptors:
            if d.adapter_id in ids:
                raise RuntimeError(f"duplicate adapter id: {d.adapter_id}")
            ids.add(d.adapter_id)
            engine=engines.get(d.engine_id)
            if engine is None:
                raise RuntimeError(f"adapter references unregistered engine: {d.engine_id}")
            allowed=set(str(x) for x in engine.get("allowed_actions",()))
            for action in d.actions:
                if action not in allowed:
                    raise RuntimeError(f"adapter action expands engine scope: {d.engine_id}:{action}")
                coverage.setdefault((d.engine_id,action),[]).append(d)
            if d.mutation_capable != bool(engine.get("mutation_capable")):
                raise RuntimeError(f"adapter mutation capability mismatch: {d.adapter_id}")
            if d.mutation_capable and (not d.gateway_required or engine.get("gateway_required") is not True):
                raise RuntimeError(f"mutating adapter must be gateway-bound: {d.adapter_id}")
            if d.plan_dispatchable and d.implementation=="internal.gateway_managed":
                raise RuntimeError(f"plan-dispatchable adapter requires executable implementation: {d.adapter_id}")

        if self.config.get("require_complete_active_engine_action_coverage") is True:
            missing=[]
            for eid,e in engines.items():
                for action in e.get("allowed_actions",()):
                    if (eid,str(action)) not in coverage:
                        missing.append(f"{eid}:{action}")
            if missing:
                raise RuntimeError("executor adapter coverage incomplete: "+", ".join(sorted(missing)))

        for key,items in coverage.items():
            plan_items=[x for x in items if x.plan_dispatchable]
            if len(plan_items)>1:
                raise RuntimeError(f"duplicate plan-dispatch adapter binding: {key[0]}:{key[1]}")

    def coverage_report(self) -> dict[str,Any]:
        engines=self._active_engines()
        total=sum(len(e.get("allowed_actions",())) for e in engines.values())
        covered={
            (d.engine_id,a)
            for d in self.descriptors
            for a in d.actions
        }
        plan=sum(len(d.actions) for d in self.descriptors if d.plan_dispatchable)
        return {
            "schema":"PHOENIX_EXECUTOR_REGISTRY_COVERAGE_V1",
            "active_engines":len(engines),
            "active_engine_actions":total,
            "covered_engine_actions":len(covered),
            "plan_dispatch_bindings":plan,
            "complete":len(covered)==total,
            "future_action_default":self.config["future_action_default"],
        }

    def descriptor_for(
        self,engine_id:str,action:str,*,plan_dispatch_only:bool=True
    ) -> ExecutorAdapterDescriptor|None:
        matches=[
            d for d in self.descriptors
            if d.engine_id==engine_id
            and action in d.actions
            and (d.plan_dispatchable or not plan_dispatch_only)
        ]
        if not matches:
            return None
        matches.sort(key=lambda x:(-x.priority,x.adapter_id))
        if len(matches)>1 and matches[0].priority==matches[1].priority:
            raise RuntimeError(f"ambiguous executor adapter: {engine_id}:{action}")
        return matches[0]

    def _load(self,d:ExecutorAdapterDescriptor):
        if d.implementation=="internal.gateway_managed":
            raise PermissionError("internal adapter is not plan-dispatchable")
        if d.adapter_id in self._instances:
            return self._instances[d.adapter_id]
        module_name,sep,attr=d.implementation.partition(":")
        if not sep:
            raise RuntimeError(f"adapter implementation invalid: {d.implementation}")
        cls=getattr(import_module(module_name),attr)
        instance=cls(self.host)
        if getattr(instance,"adapter_id",None)!=d.adapter_id:
            raise RuntimeError(f"adapter implementation identity mismatch: {d.adapter_id}")
        self._instances[d.adapter_id]=instance
        return instance

    def resolve(self,engine_id:str,action:str):
        descriptor=self.descriptor_for(engine_id,action,plan_dispatch_only=True)
        if descriptor is None:
            return None
        return descriptor,self._load(descriptor)

    def assert_future_engine_admission(self,engine:dict[str,Any],adapters:list[dict[str,Any]]) -> None:
        if not engine.get("engine_id"):
            raise PermissionError("future engine missing unique engine id")
        if engine.get("status")!="ACTIVE":
            raise PermissionError("future engine must be ACTIVE for admission")
        if engine.get("mutation_capable") and engine.get("gateway_required") is not True:
            raise PermissionError("future mutating engine must require gateway")
        covered=set()
        for raw in adapters:
            d=ExecutorAdapterDescriptor.from_dict(raw)
            if d.engine_id!=engine["engine_id"]:
                raise PermissionError("future adapter engine binding mismatch")
            if d.mutation_capable != bool(engine.get("mutation_capable")):
                raise PermissionError("future adapter mutation capability mismatch")
            if d.mutation_capable and not d.gateway_required:
                raise PermissionError("future mutating adapter must require gateway")
            covered.update(d.actions)
        missing=set(engine.get("allowed_actions",()))-covered
        if missing:
            raise PermissionError("future engine action coverage missing: "+", ".join(sorted(missing)))
