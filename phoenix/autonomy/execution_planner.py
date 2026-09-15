from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import hashlib
import json
import re

from .decision_engine import ActionRequest, AutonomyDecisionEngine


def _slug(value: str) -> str:
    s=re.sub(r"[^a-zA-Z0-9_-]+","-",str(value)).strip("-").lower()
    return s or "goal"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode("utf-8")


@dataclass(frozen=True)
class GoalSpec:
    goal_id: str
    objective: str
    goal_type: str
    domain: str
    success_criteria: tuple[str,...]
    constraints: tuple[str,...]=()
    available_gates: tuple[str,...]=()
    context: dict[str,Any]=field(default_factory=dict)
    subgoals: tuple["GoalSpec",...]=()

    @classmethod
    def from_dict(cls,data:dict[str,Any]) -> "GoalSpec":
        if data.get("schema","PHOENIX_GOAL_SPEC_V1")!="PHOENIX_GOAL_SPEC_V1":
            raise ValueError("goal schema invalid")
        return cls(
            goal_id=str(data["goal_id"]),
            objective=str(data["objective"]),
            goal_type=str(data.get("goal_type","generic.analysis")),
            domain=str(data.get("domain","general")),
            success_criteria=tuple(str(x) for x in data.get("success_criteria",())),
            constraints=tuple(str(x) for x in data.get("constraints",())),
            available_gates=tuple(sorted(set(str(x) for x in data.get("available_gates",())))),
            context=dict(data.get("context",{})),
            subgoals=tuple(cls.from_dict(x) for x in data.get("subgoals",())),
        )

    def to_dict(self) -> dict[str,Any]:
        return {
            "schema":"PHOENIX_GOAL_SPEC_V1",
            "goal_id":self.goal_id,
            "objective":self.objective,
            "goal_type":self.goal_type,
            "domain":self.domain,
            "success_criteria":list(self.success_criteria),
            "constraints":list(self.constraints),
            "available_gates":list(self.available_gates),
            "context":self.context,
            "subgoals":[x.to_dict() for x in self.subgoals],
        }


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    goal_id: str
    key: str
    title: str
    action: str
    risk: str
    mutating: bool
    domain: str
    engine_id: str
    paths: tuple[str,...]
    dependencies: tuple[str,...]
    proposed_gates: tuple[str,...]
    policy_effect: str
    policy_rule_id: str
    policy_execution_authorized: bool
    required_gates: tuple[str,...]
    missing_gates: tuple[str,...]
    step_status: str
    gateway_required: bool
    policy_bundle_sha256: str

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    goal_id: str
    objective: str
    goal_type: str
    domain: str
    status: str
    north_star_id: str
    north_star_version: str
    policy_version: str
    policy_bundle_sha256: str
    planner_backend: str
    goal_sha256: str
    steps: tuple[PlanStep,...]
    topological_order: tuple[str,...]
    execution_batches: tuple[tuple[str,...],...]
    summary: dict[str,int]
    plan_sha256: str

    def to_dict(self) -> dict[str,Any]:
        d=asdict(self)
        d["schema"]="PHOENIX_EXECUTION_PLAN_V1"
        d["steps"]=[s.to_dict() for s in self.steps]
        d["topological_order"]=list(self.topological_order)
        d["execution_batches"]=[list(x) for x in self.execution_batches]
        return d


class NativeDag:
    name="native_kahn"

    @staticmethod
    def topological(nodes:tuple[str,...],deps:dict[str,tuple[str,...]]) -> tuple[tuple[str,...],tuple[tuple[str,...],...]]:
        node_set=set(nodes)
        for node in nodes:
            for dep in deps.get(node,()):
                if dep not in node_set:
                    raise RuntimeError(f"unknown dependency {dep} for {node}")
        incoming={n:set(deps.get(n,())) for n in nodes}
        outgoing={n:set() for n in nodes}
        for n,ds in incoming.items():
            for d in ds:
                outgoing[d].add(n)

        order=[]
        batches=[]
        remaining=set(nodes)
        while remaining:
            ready=tuple(sorted(n for n in remaining if not incoming[n]))
            if not ready:
                raise RuntimeError("execution plan contains dependency cycle")
            batches.append(ready)
            for n in ready:
                order.append(n)
                remaining.remove(n)
                for nxt in outgoing[n]:
                    incoming[nxt].discard(n)
        return tuple(order),tuple(batches)


class DagAdapter:
    def __init__(self):
        self.backend="native_kahn"
        self._nx=None
        try:
            import networkx as nx
            self._nx=nx
            self.backend="networkx"
        except Exception:
            self._nx=None

    def topological(self,nodes,dependencies):
        if self._nx is None:
            return NativeDag.topological(tuple(nodes),dependencies)
        g=self._nx.DiGraph()
        for n in nodes:
            g.add_node(n)
        for n in nodes:
            for dep in dependencies.get(n,()):
                if dep not in g:
                    raise RuntimeError(f"unknown dependency {dep} for {n}")
                g.add_edge(dep,n)
        if not self._nx.is_directed_acyclic_graph(g):
            raise RuntimeError("execution plan contains dependency cycle")
        order=tuple(self._nx.lexicographical_topological_sort(g,key=lambda x:x))
        generations=tuple(
            tuple(sorted(x))
            for x in self._nx.topological_generations(g)
        )
        return order,generations


class AutonomousExecutionPlanner:
    def __init__(
        self,
        repo_root:Path,
        decision_engine:AutonomyDecisionEngine|None=None,
        planner_policy:dict[str,Any]|None=None,
        template_registry:dict[str,Any]|None=None,
        engine_registry:dict[str,Any]|None=None,
        dag_adapter:DagAdapter|None=None,
    ):
        self.repo_root=Path(repo_root).resolve()
        cfg=self.repo_root/"configs/phoenix"
        self.decision_engine=decision_engine or AutonomyDecisionEngine.from_repo(self.repo_root)
        self.planner_policy=planner_policy or json.loads(
            (cfg/"execution_planner_policy_v1.json").read_text(encoding="utf-8-sig")
        )
        self.template_registry=template_registry or json.loads(
            (cfg/"goal_template_registry_v1.json").read_text(encoding="utf-8-sig")
        )
        self.engine_registry=engine_registry or json.loads(
            (cfg/"engine_registry_v1.json").read_text(encoding="utf-8-sig")
        )
        self.dag=dag_adapter or DagAdapter()
        self._validate_contract()

    def _validate_contract(self):
        if self.planner_policy.get("schema")!="PHOENIX_EXECUTION_PLANNER_POLICY_V1":
            raise RuntimeError("execution planner policy schema invalid")
        if self.planner_policy.get("status")!="ACTIVE" or self.planner_policy.get("fail_closed") is not True:
            raise RuntimeError("execution planner must be active and fail closed")
        if self.planner_policy.get("central_policy_evaluation_required_for_every_step") is not True:
            raise RuntimeError("central policy evaluation invariant missing")
        if self.planner_policy.get("universal_gateway_required_at_every_mutation_boundary") is not True:
            raise RuntimeError("universal gateway mutation boundary invariant missing")
        if self.planner_policy.get("plan_only_does_not_issue_mutation_permits") is not True:
            raise RuntimeError("planner may not pre-issue mutation permits")
        if self.template_registry.get("schema")!="PHOENIX_GOAL_TEMPLATE_REGISTRY_V1":
            raise RuntimeError("goal template registry schema invalid")

    def _validate_goal(self,goal:GoalSpec,depth:int=0) -> int:
        b=self.planner_policy["bounds"]
        if depth>int(b["max_goal_depth"]):
            raise RuntimeError("goal decomposition depth exceeds policy")
        if not goal.goal_id or len(goal.goal_id)>128:
            raise ValueError("goal_id invalid")
        if not goal.objective or len(goal.objective)>int(b["max_objective_chars"]):
            raise ValueError("objective invalid")
        if not goal.success_criteria:
            raise ValueError("at least one success criterion required")
        if len(goal.subgoals)>int(b["max_subgoals_per_goal"]):
            raise RuntimeError("subgoal fanout exceeds policy")
        count=1
        for sg in goal.subgoals:
            count+=self._validate_goal(sg,depth+1)
        return count

    def _template(self,goal:GoalSpec) -> dict[str,Any]:
        templates=self.template_registry["templates"]
        key=goal.goal_type
        if key not in templates:
            key=self.planner_policy["defaults"]["unknown_goal_type"]
        if key not in templates:
            raise RuntimeError("safe fallback goal template missing")
        return templates[key]

    def _resolve_paths(self,goal:GoalSpec,spec:dict[str,Any]) -> tuple[str,...]:
        values=[]
        key=spec.get("paths_context_key")
        if key:
            raw=goal.context.get(key,())
            if isinstance(raw,str):
                raw=(raw,)
            values.extend(str(x) for x in raw)
        if not values:
            for item in spec.get("default_paths",()):
                values.append(str(item).replace("{goal_id}",_slug(goal.goal_id)))
        return tuple(x.replace("\\","/").lstrip("./") for x in values)

    def _registered_engine(self,engine_id:str) -> dict[str,Any]|None:
        for e in self.engine_registry.get("engines",()):
            if e.get("engine_id")==engine_id and e.get("status")=="ACTIVE":
                return e
        return None

    def _build_goal_steps(
        self,
        goal:GoalSpec,
        *,
        prefix:str,
        inherited_gates:tuple[str,...],
        depth:int,
        out:list[dict[str,Any]],
    ) -> tuple[str,str]:
        template=self._template(goal)
        specs=list(template["steps"])
        if not specs:
            raise RuntimeError("goal template has no steps")

        local_ids={s["key"]:f"{prefix}.{s['key']}" for s in specs}
        for spec in specs:
            deps=tuple(local_ids[d] for d in spec.get("depends_on",()))
            out.append({
                "step_id":local_ids[spec["key"]],
                "goal":goal,
                "spec":spec,
                "dependencies":list(deps),
                "depth":depth,
                "inherited_gates":inherited_gates,
            })

        first=local_ids[specs[0]["key"]]
        last=local_ids[specs[-1]["key"]]

        if goal.subgoals:
            child_lasts=[]
            for idx,subgoal in enumerate(goal.subgoals,1):
                child_prefix=f"{prefix}.sg{idx}-{_slug(subgoal.goal_id)}"
                child_first,child_last=self._build_goal_steps(
                    subgoal,
                    prefix=child_prefix,
                    inherited_gates=tuple(sorted(set(inherited_gates)|set(subgoal.available_gates))),
                    depth=depth+1,
                    out=out,
                )
                for row in out:
                    if row["step_id"]==child_first and first not in row["dependencies"]:
                        row["dependencies"].append(first)
                        row["dependencies"].sort()
                        break
                child_lasts.append(child_last)
            for row in out:
                if row["step_id"]==last:
                    row["dependencies"]=sorted(set(row["dependencies"])|set(child_lasts))
                    break
        return first,last

    def plan(self,goal:GoalSpec) -> ExecutionPlan:
        self._validate_goal(goal)
        rows=[]
        root_prefix=f"g-{_slug(goal.goal_id)}"
        self._build_goal_steps(
            goal,
            prefix=root_prefix,
            inherited_gates=goal.available_gates,
            depth=0,
            out=rows,
        )
        max_steps=int(self.planner_policy["bounds"]["max_steps_total"])
        if len(rows)>max_steps:
            raise RuntimeError("execution plan step count exceeds policy")

        step_ids=tuple(r["step_id"] for r in rows)
        deps={r["step_id"]:tuple(r["dependencies"]) for r in rows}
        topo,batches=self.dag.topological(step_ids,deps)

        result=[]
        counts={"READY":0,"GATED_PENDING":0,"ESCALATE":0,"DENY":0,"DENY_UNREGISTERED_ENGINE":0}
        by_id={r["step_id"]:r for r in rows}

        for step_id in topo:
            row=by_id[step_id]
            goal_for_step=row["goal"]
            spec=row["spec"]
            paths=self._resolve_paths(goal_for_step,spec)
            # Only gates that are actually satisfied may be supplied to the
            # policy engine. Template gates are expectations/documentation, not
            # proof that a gate has already passed.
            proposed=tuple(sorted(set(row["inherited_gates"])))
            decision=self.decision_engine.evaluate(ActionRequest(
                action=str(spec["action"]),
                risk=str(spec["risk"]),
                mutating=bool(spec["mutating"]),
                domain=str(spec.get("domain",goal_for_step.domain)),
                paths=paths,
                external_effect=bool(spec.get("external_effect",False)),
                gates=proposed,
                actor="autonomy.execution_planner",
                metadata={
                    "plan_only":True,
                    "goal_id":goal_for_step.goal_id,
                    "step_id":step_id,
                    "target_engine_id":spec.get("engine_id",""),
                },
            ))

            if decision.effect=="DENY":
                status="DENY"
            elif decision.effect=="ESCALATE":
                status="ESCALATE"
            elif decision.execution_authorized:
                status="READY"
            else:
                status="GATED_PENDING"

            engine_id=str(spec.get("engine_id",""))
            gateway_required=bool(spec["mutating"])
            engine=self._registered_engine(engine_id) if engine_id else None

            if bool(spec["mutating"]) and decision.execution_authorized:
                if engine is None or engine.get("mutation_capable") is not True or engine.get("gateway_required") is not True:
                    status="DENY_UNREGISTERED_ENGINE"

            counts[status]+=1
            result.append(PlanStep(
                step_id=step_id,
                goal_id=goal_for_step.goal_id,
                key=str(spec["key"]),
                title=str(spec["title"]),
                action=str(spec["action"]),
                risk=str(spec["risk"]),
                mutating=bool(spec["mutating"]),
                domain=str(spec.get("domain",goal_for_step.domain)),
                engine_id=engine_id,
                paths=paths,
                dependencies=tuple(deps[step_id]),
                proposed_gates=proposed,
                policy_effect=decision.effect,
                policy_rule_id=decision.rule_id,
                policy_execution_authorized=decision.execution_authorized,
                required_gates=decision.required_gates,
                missing_gates=decision.missing_gates,
                step_status=status,
                gateway_required=gateway_required,
                policy_bundle_sha256=decision.policy_bundle_sha256,
            ))

        if counts["DENY"] or counts["DENY_UNREGISTERED_ENGINE"]:
            overall="BLOCKED"
        elif counts["ESCALATE"]:
            overall="HUMAN_DECISION_REQUIRED"
        elif counts["GATED_PENDING"]:
            overall="GATED"
        else:
            overall="READY"

        goal_dict=goal.to_dict()
        goal_hash=hashlib.sha256(_canonical(goal_dict)).hexdigest()

        stable_steps=[]
        for s in result:
            d=s.to_dict()
            stable_steps.append(d)
        stable={
            "goal_sha256":goal_hash,
            "status":overall,
            "policy_bundle_sha256":self.decision_engine.bundle_sha256,
            "planner_backend":self.dag.backend,
            "steps":stable_steps,
            "topological_order":list(topo),
            "execution_batches":[list(x) for x in batches],
        }
        plan_hash=hashlib.sha256(_canonical(stable)).hexdigest()

        return ExecutionPlan(
            plan_id="PLAN-"+goal_hash[:16].upper(),
            goal_id=goal.goal_id,
            objective=goal.objective,
            goal_type=goal.goal_type,
            domain=goal.domain,
            status=overall,
            north_star_id=str(self.decision_engine.north_star["north_star_id"]),
            north_star_version=str(self.decision_engine.north_star["version"]),
            policy_version=str(self.decision_engine.policy["version"]),
            policy_bundle_sha256=self.decision_engine.bundle_sha256,
            planner_backend=self.dag.backend,
            goal_sha256=goal_hash,
            steps=tuple(result),
            topological_order=topo,
            execution_batches=batches,
            summary=counts,
            plan_sha256=plan_hash,
        )


class ExecutionCoordinator:
    """Produces execution tickets only; it never performs the mutation itself."""

    def next_ready(self,plan:ExecutionPlan,completed_steps:set[str]|tuple[str,...]=()) -> tuple[PlanStep,...]:
        completed=set(completed_steps)
        out=[]
        for s in plan.steps:
            if s.step_id in completed:
                continue
            if s.step_status!="READY":
                continue
            if all(dep in completed for dep in s.dependencies):
                out.append(s)
        return tuple(out)

    def execution_ticket(self,step:PlanStep) -> dict[str,Any]:
        if step.step_status!="READY":
            raise PermissionError(f"step is not READY: {step.step_status}")
        if step.mutating and not step.gateway_required:
            raise RuntimeError("mutating execution ticket must require universal gateway")
        return {
            "schema":"PHOENIX_EXECUTION_TICKET_V1",
            "step_id":step.step_id,
            "engine_id":step.engine_id,
            "action":step.action,
            "risk":step.risk,
            "domain":step.domain,
            "paths":list(step.paths),
            "gates":list(step.proposed_gates),
            "gateway_required":step.gateway_required,
            "policy_bundle_sha256":step.policy_bundle_sha256,
            "note":"This ticket is not a gateway permit. The actual mutator must obtain and consume a one-time permit.",
        }
