from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import fnmatch
import hashlib
import json
import os
import time
import uuid

from .decision_engine import ActionRequest, AutonomyDecisionEngine, PolicyDecisionLog


def _norm(path: str) -> str:
    return str(path).replace("\\","/").lstrip("./")


def _canonical(data: dict[str,Any]) -> bytes:
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class MutationIntent:
    engine_id: str
    action: str
    risk: str
    domain: str
    paths: tuple[str,...]=()
    gates: tuple[str,...]=()
    external_effect: bool=False
    flags: tuple[str,...]=()
    metadata: dict[str,Any]=field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self,"paths",tuple(_norm(x) for x in self.paths))
        object.__setattr__(self,"gates",tuple(sorted(set(self.gates))))
        object.__setattr__(self,"flags",tuple(sorted(set(self.flags))))


@dataclass(frozen=True)
class GatewayPermit:
    permit_id: str
    engine_id: str
    action: str
    paths: tuple[str,...]
    decision_id: str
    policy_bundle_sha256: str
    issued_at: int
    expires_at: int
    nonce: str
    fingerprint: str

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


class GatewayAuditLog:
    def __init__(self,path:Path):
        self.path=Path(path)

    def append(self,event_type:str,payload:dict[str,Any]) -> None:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        row={
            "schema":"PHOENIX_UNIVERSAL_GATEWAY_AUDIT_EVENT_V1",
            "event_type":event_type,
            "timestamp":int(time.time()),
            "payload":payload,
        }
        with self.path.open("a",encoding="utf-8",newline="\n") as f:
            f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
            f.flush()
            os.fsync(f.fileno())


class UniversalAutonomyGateway:
    def __init__(
        self,
        decision_engine:AutonomyDecisionEngine,
        gateway_policy:dict,
        engine_registry:dict,
        audit_log:GatewayAuditLog|None=None,
    ):
        self.decision_engine=decision_engine
        self.gateway_policy=gateway_policy
        self.engine_registry=engine_registry
        self.audit_log=audit_log
        self._active:dict[str,dict[str,Any]]={}
        self._validate_contract()

    @classmethod
    def from_repo(
        cls,
        repo_root:Path,
        decision_log:PolicyDecisionLog|None=None,
        audit_log:GatewayAuditLog|None=None,
    ) -> "UniversalAutonomyGateway":
        repo=Path(repo_root).resolve()
        cfg=repo/"configs/phoenix"
        decision=AutonomyDecisionEngine.from_repo(repo,decision_log)
        gp=json.loads((cfg/"universal_gateway_policy_v1.json").read_text(encoding="utf-8-sig"))
        reg=json.loads((cfg/"engine_registry_v1.json").read_text(encoding="utf-8-sig"))
        return cls(decision,gp,reg,audit_log)

    def _validate_contract(self) -> None:
        if self.gateway_policy.get("schema")!="PHOENIX_UNIVERSAL_AUTONOMY_GATEWAY_POLICY_V1":
            raise RuntimeError("universal gateway policy schema invalid")
        if self.gateway_policy.get("enabled") is not True or self.gateway_policy.get("fail_closed") is not True:
            raise RuntimeError("universal gateway must be enabled and fail closed")
        if self.gateway_policy.get("future_engine_default")!="DENY_UNREGISTERED":
            raise RuntimeError("future engine default must deny unregistered mutation")
        permit=self.gateway_policy.get("permit",{})
        for key in (
            "required","one_time_use","exact_engine_binding","exact_action_binding",
            "exact_path_binding","policy_bundle_binding","decision_binding",
        ):
            if permit.get(key) is not True:
                raise RuntimeError(f"gateway permit invariant missing: {key}")
        ttl=int(permit.get("ttl_seconds",0))
        if ttl<1 or ttl>3600:
            raise RuntimeError("gateway permit TTL invalid")

        if self.engine_registry.get("schema")!="PHOENIX_ENGINE_REGISTRY_V1":
            raise RuntimeError("engine registry schema invalid")
        if self.engine_registry.get("status")!="ACTIVE" or self.engine_registry.get("fail_closed") is not True:
            raise RuntimeError("engine registry must be active and fail closed")
        if self.engine_registry.get("future_engine_default")!="DENY_UNTIL_REGISTERED":
            raise RuntimeError("engine registry future default invalid")

        ids=[]
        for engine in self.engine_registry.get("engines",[]):
            eid=str(engine.get("engine_id",""))
            if not eid:
                raise RuntimeError("registered engine missing engine_id")
            ids.append(eid)
            if engine.get("mutation_capable") is True:
                if engine.get("gateway_required") is not True:
                    raise RuntimeError(f"mutation-capable engine lacks gateway requirement: {eid}")
                if not engine.get("allowed_actions"):
                    raise RuntimeError(f"mutation-capable engine lacks allowed actions: {eid}")
                if not engine.get("allowed_domains"):
                    raise RuntimeError(f"mutation-capable engine lacks allowed domains: {eid}")
        if len(ids)!=len(set(ids)):
            raise RuntimeError("duplicate engine_id in registry")

    def _engine(self,engine_id:str) -> dict[str,Any]:
        for engine in self.engine_registry.get("engines",[]):
            if engine.get("engine_id")==engine_id and engine.get("status")=="ACTIVE":
                return engine
        raise PermissionError(f"UNREGISTERED_ENGINE_DENY:{engine_id}")

    def _check_registry_scope(self,engine:dict,intent:MutationIntent) -> None:
        if engine.get("mutation_capable") is not True or engine.get("gateway_required") is not True:
            raise PermissionError("ENGINE_NOT_ADMITTED_FOR_MUTATION")
        actions=engine.get("allowed_actions",[])
        if not any(fnmatch.fnmatchcase(intent.action,p) for p in actions):
            raise PermissionError(f"ENGINE_ACTION_DENY:{intent.action}")
        domains=engine.get("allowed_domains",[])
        if intent.domain not in domains:
            raise PermissionError(f"ENGINE_DOMAIN_DENY:{intent.domain}")

        exact={_norm(x).lower() for x in engine.get("allowed_exact_paths",[])}
        roots=[_norm(x).lower() for x in engine.get("allowed_path_roots",[])]
        if intent.paths:
            for path in intent.paths:
                low=_norm(path).lower()
                if exact and low in exact:
                    continue
                if roots and any(low.startswith(root) for root in roots):
                    continue
                if exact or roots:
                    raise PermissionError(f"ENGINE_PATH_SCOPE_DENY:{path}")

    def _fingerprint_fields(
        self,permit_id,engine_id,action,paths,decision_id,bundle,issued,expires,nonce
    ) -> str:
        obj={
            "permit_id":permit_id,
            "engine_id":engine_id,
            "action":action,
            "paths":list(paths),
            "decision_id":decision_id,
            "policy_bundle_sha256":bundle,
            "issued_at":issued,
            "expires_at":expires,
            "nonce":nonce,
        }
        return hashlib.sha256(_canonical(obj)).hexdigest()

    def authorize(self,intent:MutationIntent) -> GatewayPermit:
        engine=self._engine(intent.engine_id)
        self._check_registry_scope(engine,intent)

        request=ActionRequest(
            action=intent.action,
            risk=intent.risk,
            mutating=True,
            domain=intent.domain,
            paths=intent.paths,
            external_effect=intent.external_effect,
            gates=intent.gates,
            flags=intent.flags,
            actor=intent.engine_id,
            metadata=intent.metadata,
        )
        decision=self.decision_engine.require_authorized(request)

        now=int(time.time())
        ttl=int(self.gateway_policy["permit"]["ttl_seconds"])
        permit_id="GWPERMIT-"+uuid.uuid4().hex[:16].upper()
        nonce=uuid.uuid4().hex
        expires=now+ttl
        bundle=decision.policy_bundle_sha256
        fingerprint=self._fingerprint_fields(
            permit_id,intent.engine_id,intent.action,intent.paths,
            decision.decision_id,bundle,now,expires,nonce
        )
        permit=GatewayPermit(
            permit_id=permit_id,
            engine_id=intent.engine_id,
            action=intent.action,
            paths=intent.paths,
            decision_id=decision.decision_id,
            policy_bundle_sha256=bundle,
            issued_at=now,
            expires_at=expires,
            nonce=nonce,
            fingerprint=fingerprint,
        )
        self._active[permit_id]={"permit":permit,"used":False}
        if self.audit_log:
            self.audit_log.append("PERMIT_ISSUED",{
                "permit":permit.to_dict(),
                "policy_effect":decision.effect,
                "rule_id":decision.rule_id,
            })
        return permit

    def consume(
        self,
        permit:GatewayPermit,
        *,
        engine_id:str,
        action:str,
        paths:tuple[str,...]=(),
    ) -> None:
        record=self._active.get(permit.permit_id)
        if record is None:
            raise PermissionError("PERMIT_UNKNOWN_OR_FOREIGN_GATEWAY")
        if record["used"]:
            raise PermissionError("PERMIT_REUSE_DENY")
        if int(time.time())>permit.expires_at:
            raise PermissionError("PERMIT_EXPIRED_DENY")

        normalized=tuple(_norm(x) for x in paths)
        if permit.engine_id!=engine_id:
            raise PermissionError("PERMIT_ENGINE_BINDING_DENY")
        if permit.action!=action:
            raise PermissionError("PERMIT_ACTION_BINDING_DENY")
        if permit.paths!=normalized:
            raise PermissionError("PERMIT_PATH_BINDING_DENY")
        if permit.policy_bundle_sha256!=self.decision_engine.bundle_sha256:
            raise PermissionError("PERMIT_POLICY_BUNDLE_BINDING_DENY")

        expected=self._fingerprint_fields(
            permit.permit_id,permit.engine_id,permit.action,permit.paths,
            permit.decision_id,permit.policy_bundle_sha256,
            permit.issued_at,permit.expires_at,permit.nonce
        )
        if expected!=permit.fingerprint:
            raise PermissionError("PERMIT_FINGERPRINT_DENY")

        record["used"]=True
        if self.audit_log:
            self.audit_log.append("PERMIT_CONSUMED",{
                "permit_id":permit.permit_id,
                "engine_id":engine_id,
                "action":action,
                "paths":list(normalized),
                "decision_id":permit.decision_id,
            })

    def assert_future_engine_admission(self,manifest:dict[str,Any]) -> None:
        """Fail-closed admission contract for every future engine."""
        engine_id=str(manifest.get("engine_id",""))
        if not engine_id:
            raise PermissionError("FUTURE_ENGINE_ID_REQUIRED")
        if manifest.get("mutation_capable") is True:
            if manifest.get("gateway_required") is not True:
                raise PermissionError("FUTURE_ENGINE_GATEWAY_REQUIRED")
            if not manifest.get("allowed_actions"):
                raise PermissionError("FUTURE_ENGINE_ACTIONS_REQUIRED")
            if not manifest.get("allowed_domains"):
                raise PermissionError("FUTURE_ENGINE_DOMAINS_REQUIRED")
            if not manifest.get("allowed_path_roots") and not manifest.get("allowed_exact_paths"):
                raise PermissionError("FUTURE_ENGINE_MUTATION_SCOPE_REQUIRED")
        # Admission to *execute* mutation still requires actual central registry entry.
        self._engine(engine_id)
