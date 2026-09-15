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

EFFECTS={"ALLOW","ALLOW_WITH_GATES","ESCALATE","DENY"}
RISKS={"LOW","MEDIUM","HIGH","CRITICAL"}


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(path: str) -> str:
    return str(path).replace("\\","/").lstrip("./")


@dataclass(frozen=True)
class ActionRequest:
    action: str
    risk: str
    mutating: bool
    domain: str="general"
    paths: tuple[str,...]=()
    external_effect: bool=False
    gates: tuple[str,...]=()
    flags: tuple[str,...]=()
    actor: str="phoenix"
    request_id: str=field(default_factory=lambda:"POLREQ-"+uuid.uuid4().hex[:12].upper())
    metadata: dict[str,Any]=field(default_factory=dict)

    def __post_init__(self):
        if self.risk not in RISKS:
            raise ValueError(f"unsupported risk: {self.risk}")
        object.__setattr__(self,"paths",tuple(_norm(x) for x in self.paths))
        object.__setattr__(self,"gates",tuple(sorted(set(self.gates))))
        object.__setattr__(self,"flags",tuple(sorted(set(self.flags))))


@dataclass(frozen=True)
class PolicyDecision:
    request_id: str
    decision_id: str
    timestamp: int
    effect: str
    execution_authorized: bool
    rule_id: str
    reason: str
    reason_codes: tuple[str,...]
    required_gates: tuple[str,...]
    satisfied_gates: tuple[str,...]
    missing_gates: tuple[str,...]
    north_star_id: str
    north_star_version: str
    policy_version: str
    policy_bundle_sha256: str
    action: str
    risk: str
    mutating: bool
    domain: str
    paths: tuple[str,...]

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


class PolicyDecisionLog:
    def __init__(self,path:Path):
        self.path=Path(path)

    def append(self,request:ActionRequest,decision:PolicyDecision) -> None:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        row={
            "schema":"PHOENIX_POLICY_DECISION_LOG_EVENT_V1",
            "request":asdict(request),
            "decision":decision.to_dict(),
        }
        with self.path.open("a",encoding="utf-8",newline="\n") as f:
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
            f.flush()
            os.fsync(f.fileno())


class AutonomyDecisionEngine:
    def __init__(self,north_star:dict,policy:dict,bundle_manifest:dict,decision_log:PolicyDecisionLog|None=None):
        self.north_star=north_star
        self.policy=policy
        self.bundle_manifest=bundle_manifest
        self.decision_log=decision_log
        self._validate_contract()

    @classmethod
    def from_repo(cls,repo_root:Path,decision_log:PolicyDecisionLog|None=None) -> "AutonomyDecisionEngine":
        repo=Path(repo_root).resolve()
        cfg=repo/"configs/phoenix"
        manifest_path=cfg/"policy_bundle_manifest_v1.json"
        if not manifest_path.is_file():
            raise RuntimeError("policy bundle manifest missing")
        manifest=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        files=manifest.get("files",{})
        required=("north_star_v1.json","autonomy_policy_v2.json")
        for name in required:
            path=cfg/name
            if not path.is_file():
                raise RuntimeError(f"policy bundle file missing: {name}")
            expected=str(files.get(name,{}).get("sha256","")).lower()
            actual=_sha256(path)
            if not expected or expected!=actual:
                raise RuntimeError(f"policy bundle integrity failure: {name}")
        north=json.loads((cfg/"north_star_v1.json").read_text(encoding="utf-8-sig"))
        policy=json.loads((cfg/"autonomy_policy_v2.json").read_text(encoding="utf-8-sig"))
        return cls(north,policy,manifest,decision_log)

    def _validate_contract(self) -> None:
        if self.north_star.get("schema")!="PHOENIX_MACHINE_READABLE_NORTH_STAR_V1":
            raise RuntimeError("North Star schema invalid")
        if self.north_star.get("status")!="ACTIVE":
            raise RuntimeError("North Star is not active")
        if self.policy.get("schema")!="PHOENIX_AUTONOMY_POLICY_V2":
            raise RuntimeError("autonomy policy schema invalid")
        if self.policy.get("fail_closed") is not True:
            raise RuntimeError("autonomy policy must fail closed")
        ns=self.policy.get("north_star",{})
        if ns.get("id")!=self.north_star.get("north_star_id") or ns.get("version")!=self.north_star.get("version"):
            raise RuntimeError("policy/North Star binding mismatch")
        machine=self.north_star.get("machine_contract",{})
        if machine.get("central_decision_engine_required_for_mutations") is not True:
            raise RuntimeError("central decision engine invariant missing")
        if machine.get("mutation_default_effect")!="DENY":
            raise RuntimeError("mutation default must DENY")
        if set(self.policy.get("effects",()))!=EFFECTS:
            raise RuntimeError("policy effect set invalid")
        rules=self.policy.get("rules",[])
        if not rules:
            raise RuntimeError("policy rules missing")
        ids=[x.get("id") for x in rules]
        if len(ids)!=len(set(ids)):
            raise RuntimeError("duplicate policy rule id")

    @property
    def bundle_sha256(self) -> str:
        return str(self.bundle_manifest.get("bundle_sha256",""))

    def _hard_deny(self,request:ActionRequest) -> tuple[str,str]|None:
        deny_flags=set(self.policy.get("hard_deny_flags",()))
        hit=sorted(set(request.flags)&deny_flags)
        if hit:
            return "HARD_DENY_FLAG:"+hit[0], "North Star hard-deny invariant"
        if request.risk=="CRITICAL":
            return "CRITICAL_RISK", "CRITICAL autonomous execution is blocked"
        return None

    def _match(self,match:dict,request:ActionRequest) -> bool:
        actions=match.get("actions")
        if actions and not any(fnmatch.fnmatchcase(request.action,p) for p in actions):
            return False
        risks=match.get("risks")
        if risks and request.risk not in risks:
            return False
        if "mutating" in match and bool(match["mutating"])!=request.mutating:
            return False
        if "external_effect" in match and bool(match["external_effect"])!=request.external_effect:
            return False
        domains=match.get("domains")
        if domains and request.domain not in domains:
            return False
        roots=match.get("path_all_under")
        if roots:
            if not request.paths:
                return False
            normalized=[_norm(x).lower() for x in roots]
            for path in request.paths:
                low=_norm(path).lower()
                if not any(low.startswith(root) for root in normalized):
                    return False
        allowlist_name=match.get("path_all_exact_allowlist")
        if allowlist_name:
            allowed={_norm(x).lower() for x in self.policy.get(allowlist_name,())}
            if not request.paths or any(_norm(x).lower() not in allowed for x in request.paths):
                return False
        return True

    def evaluate(self,request:ActionRequest,log:bool=True) -> PolicyDecision:
        hard=self._hard_deny(request)
        if hard:
            decision=self._decision(request,"DENY","NORTH_STAR_HARD_DENY",hard[1],(hard[0],),())
            if log and self.decision_log: self.decision_log.append(request,decision)
            return decision

        rules=sorted(self.policy["rules"],key=lambda x:int(x.get("priority",0)),reverse=True)
        for rule in rules:
            if self._match(rule.get("match",{}),request):
                effect=str(rule["effect"])
                required=tuple(rule.get("required_gates",()))
                decision=self._decision(
                    request,effect,str(rule["id"]),str(rule.get("reason","")),
                    ("RULE_MATCH",str(rule["id"])),required
                )
                if log and self.decision_log: self.decision_log.append(request,decision)
                return decision

        default_effect=self.policy.get("defaults",{}).get("mutating" if request.mutating else "read_only","DENY")
        decision=self._decision(
            request,str(default_effect),"DEFAULT_FAIL_CLOSED","No explicit policy rule matched.",
            ("DEFAULT_FAIL_CLOSED",),()
        )
        if log and self.decision_log: self.decision_log.append(request,decision)
        return decision

    def _decision(self,request,effect,rule_id,reason,reason_codes,required):
        if effect not in EFFECTS:
            raise RuntimeError(f"invalid policy effect: {effect}")
        satisfied=tuple(sorted(set(request.gates)&set(required)))
        missing=tuple(sorted(set(required)-set(request.gates)))
        authorized=(effect=="ALLOW") or (effect=="ALLOW_WITH_GATES" and not missing)
        return PolicyDecision(
            request_id=request.request_id,
            decision_id="POLDEC-"+uuid.uuid4().hex[:12].upper(),
            timestamp=int(time.time()),
            effect=effect,
            execution_authorized=authorized,
            rule_id=rule_id,
            reason=reason,
            reason_codes=tuple(reason_codes),
            required_gates=tuple(required),
            satisfied_gates=satisfied,
            missing_gates=missing,
            north_star_id=str(self.north_star["north_star_id"]),
            north_star_version=str(self.north_star["version"]),
            policy_version=str(self.policy["version"]),
            policy_bundle_sha256=self.bundle_sha256,
            action=request.action,
            risk=request.risk,
            mutating=request.mutating,
            domain=request.domain,
            paths=request.paths,
        )

    def require_authorized(self,request:ActionRequest) -> PolicyDecision:
        decision=self.evaluate(request)
        if not decision.execution_authorized:
            raise PermissionError(
                f"policy blocked action {request.action}: {decision.effect}; "
                f"rule={decision.rule_id}; missing_gates={','.join(decision.missing_gates)}"
            )
        return decision
