from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import re
import time
import uuid

from .approval_resume import LocalIntegrityKey
from .decision_engine import ActionRequest, AutonomyDecisionEngine, PolicyDecisionLog
from .executor_adapter_registry import UniversalCapabilityExecutorRegistry
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway


ENGINE_ID_RE=re.compile(r"^[a-z0-9][a-z0-9_.-]{2,159}$")
ACTION_RE=re.compile(r"^[a-z0-9][a-z0-9_.:-]{1,159}$")
ADAPTER_ID_RE=re.compile(r"^[a-z0-9][a-z0-9_.-]{2,199}$")


def _canonical(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _sha(obj:Any)->str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _safe(value:str)->str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in str(value))


@dataclass(frozen=True)
class DiscoveryRecord:
    source_type: str
    source: str
    status: str
    sha256: str|None
    engine_id: str|None
    details: dict[str,Any]

    def to_dict(self)->dict[str,Any]:
        return {
            "source_type":self.source_type,
            "source":self.source,
            "status":self.status,
            "sha256":self.sha256,
            "engine_id":self.engine_id,
            "details":self.details,
        }


class EngineManifestDiscovery:
    def __init__(self,repo_root:Path,policy:dict[str,Any]):
        self.repo_root=Path(repo_root).resolve()
        self.policy=policy

    def repository_manifests(self)->tuple[DiscoveryRecord,...]:
        pattern=self.policy["discovery"]["repository_manifest_glob"]
        max_count=int(self.policy["discovery"]["max_manifests_per_run"])
        max_bytes=int(self.policy["discovery"]["max_manifest_bytes"])
        out=[]
        for path in sorted(self.repo_root.glob(pattern)):
            parts={x.lower() for x in path.parts}
            if ".git" in parts or "__pycache__" in parts:
                continue
            if not path.is_file():
                continue
            if len(out)>=max_count:
                raise RuntimeError("engine manifest discovery count bound exceeded")
            size=path.stat().st_size
            if size>max_bytes:
                out.append(DiscoveryRecord(
                    "repository_manifest",str(path),"REJECT_OVERSIZE",None,None,{"bytes":size}
                ))
                continue
            raw=path.read_bytes()
            digest=hashlib.sha256(raw).hexdigest()
            try:
                data=json.loads(raw.decode("utf-8-sig"))
                out.append(DiscoveryRecord(
                    "repository_manifest",str(path),"DISCOVERED",digest,
                    str(data.get("engine_id")) if data.get("engine_id") else None,
                    {"schema":data.get("schema"),"bytes":size}
                ))
            except Exception as exc:
                out.append(DiscoveryRecord(
                    "repository_manifest",str(path),"REJECT_INVALID_JSON",digest,None,
                    {"error":type(exc).__name__,"bytes":size}
                ))
        return tuple(out)

    def entry_points(self)->tuple[DiscoveryRecord,...]:
        group=str(self.policy["discovery"]["entry_point_group"])
        records=[]
        eps=importlib_metadata.entry_points()
        selected=eps.select(group=group) if hasattr(eps,"select") else eps.get(group,())
        for ep in sorted(selected,key=lambda x:(x.name,x.value)):
            dist_name=None
            dist_version=None
            try:
                if ep.dist:
                    dist_name=ep.dist.metadata.get("Name")
                    dist_version=ep.dist.version
            except Exception:
                pass
            records.append(DiscoveryRecord(
                "python_entry_point",
                f"{group}:{ep.name}",
                "DISCOVERED_NOT_LOADED",
                None,
                None,
                {
                    "name":ep.name,
                    "value":ep.value,
                    "distribution":dist_name,
                    "version":dist_version,
                    "code_loaded":False,
                }
            ))
        return tuple(records)


class EngineOnboardingService:
    def __init__(
        self,
        repo_root:Path,
        runtime_root:Path,
        *,
        gateway:UniversalAutonomyGateway|None=None,
    ):
        self.repo_root=Path(repo_root).resolve()
        self.runtime_root=Path(runtime_root)
        cfg=self.repo_root/"configs/phoenix"
        self.policy=json.loads((cfg/"engine_onboarding_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.engine_registry=json.loads((cfg/"engine_registry_v1.json").read_text(encoding="utf-8-sig"))
        self.executor_registry_config=json.loads((cfg/"capability_executor_registry_v1.json").read_text(encoding="utf-8-sig"))
        self.future_contract=json.loads((cfg/"future_engine_admission_contract_v1.json").read_text(encoding="utf-8-sig"))
        self.decision_engine=AutonomyDecisionEngine.from_repo(self.repo_root)

        if gateway is None:
            gateway=UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(
                    self.runtime_root/"policy_decisions"/"decisions_v1.jsonl"
                ),
                audit_log=GatewayAuditLog(
                    self.runtime_root/"gateway"/"audit_v1.jsonl"
                ),
            )
        self.gateway=gateway
        self.phase5_registry=UniversalCapabilityExecutorRegistry(
            self.executor_registry_config,self.engine_registry
        )
        self.integrity_key=LocalIntegrityKey(
            self.runtime_root/"integrity"/"engine_onboarding_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self):
        if self.policy.get("schema")!="PHOENIX_ENGINE_ONBOARDING_POLICY_V1":
            raise RuntimeError("engine onboarding policy schema invalid")
        if self.policy.get("status")!="ACTIVE" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("engine onboarding must be active and fail closed")
        if self.policy["activation"].get("automatic_mutating_engine_activation") is not False:
            raise RuntimeError("automatic mutation engine activation must remain disabled")
        if self.policy["discovery"].get("arbitrary_module_import") is not False:
            raise RuntimeError("untrusted discovery import must remain disabled")

    def _sign(self,obj:dict[str,Any])->str:
        return hmac.new(self.integrity_key,_canonical(obj),hashlib.sha256).hexdigest()

    def verify_signed_artifact(self,obj:dict[str,Any],field:str="hmac_sha256")->bool:
        supplied=str(obj.get(field,""))
        unsigned=dict(obj)
        unsigned.pop(field,None)
        return bool(supplied) and hmac.compare_digest(supplied,self._sign(unsigned))

    def _write_runtime(
        self,
        *,
        rel_path:str,
        obj:dict[str,Any],
        action:str,
        gates:tuple[str,...],
    )->Path:
        rel=rel_path.replace("\\","/").lstrip("/")
        uri=f"runtime://engine_onboarding/{rel}"
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.engine_onboarding",
            action=action,
            risk="LOW",
            domain="onboarding",
            paths=(uri,),
            gates=gates,
            metadata={"artifact":rel,"sha256":_sha(obj)},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.engine_onboarding",
            action=action,
            paths=(uri,),
        )
        path=self.runtime_root/"engine_onboarding"/Path(rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        os.replace(tmp,path)
        return path

    def _write_text_runtime(
        self,
        *,
        rel_path:str,
        text:str,
        action:str,
        gates:tuple[str,...],
    )->Path:
        rel=rel_path.replace("\\","/").lstrip("/")
        uri=f"runtime://engine_onboarding/{rel}"
        digest=hashlib.sha256(text.encode("utf-8")).hexdigest()
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.engine_onboarding",
            action=action,
            risk="LOW",
            domain="onboarding",
            paths=(uri,),
            gates=gates,
            metadata={"artifact":rel,"sha256":digest},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.engine_onboarding",
            action=action,
            paths=(uri,),
        )
        path=self.runtime_root/"engine_onboarding"/Path(rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(text,encoding="utf-8",newline="\n")
        os.replace(tmp,path)
        return path

    def discover(self,persist:bool=True)->dict[str,Any]:
        discovery=EngineManifestDiscovery(self.repo_root,self.policy)
        records=[
            *[x.to_dict() for x in discovery.repository_manifests()],
            *[x.to_dict() for x in discovery.entry_points()],
        ]
        snapshot={
            "schema":"PHOENIX_ENGINE_DISCOVERY_SNAPSHOT_V1",
            "snapshot_id":"ENGDISC-"+uuid.uuid4().hex[:16].upper(),
            "timestamp":int(time.time()),
            "repository":str(self.repo_root),
            "code_loaded_during_discovery":False,
            "records":records,
        }
        unsigned=dict(snapshot)
        snapshot["hmac_sha256"]=self._sign(unsigned)
        if persist:
            self._write_runtime(
                rel_path=f"discovery/{snapshot['snapshot_id']}.json",
                obj=snapshot,
                action="engine.discovery.snapshot.write",
                gates=("audit_log","onboarding_integrity"),
            )
        return snapshot

    def _semantic_validate(self,candidate:dict[str,Any])->list[str]:
        errors=[]
        if candidate.get("schema")!="PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1":
            errors.append("schema")
        engine_id=str(candidate.get("engine_id",""))
        if not ENGINE_ID_RE.match(engine_id):
            errors.append("engine_id")
        actions=[str(x) for x in candidate.get("allowed_actions",())]
        domains=[str(x) for x in candidate.get("allowed_domains",())]
        if not actions or len(set(actions))!=len(actions) or any(not ACTION_RE.match(x) for x in actions):
            errors.append("allowed_actions")
        if not domains or len(set(domains))!=len(domains):
            errors.append("allowed_domains")
        mutating=bool(candidate.get("mutation_capable"))
        if mutating and candidate.get("gateway_required") is not True:
            errors.append("gateway_required")
        if mutating and not (
            candidate.get("allowed_path_roots") or candidate.get("allowed_exact_paths")
        ):
            errors.append("mutation_scope")

        profiles=candidate.get("action_profiles",())
        profile_actions=[str(x.get("action","")) for x in profiles]
        if set(profile_actions)!=set(actions) or len(profile_actions)!=len(actions):
            errors.append("action_profiles_coverage")
        for profile in profiles:
            if profile.get("domain") not in domains:
                errors.append(f"profile_domain:{profile.get('action')}")
            if bool(profile.get("mutating")) != mutating:
                errors.append(f"profile_mutation:{profile.get('action')}")

        adapters=candidate.get("adapters",())
        covered=set()
        for raw in adapters:
            aid=str(raw.get("adapter_id",""))
            if not ADAPTER_ID_RE.match(aid):
                errors.append(f"adapter_id:{aid}")
            a_actions={str(x) for x in raw.get("actions",())}
            if not a_actions or not a_actions<=set(actions):
                errors.append(f"adapter_action_scope:{aid}")
            covered|=a_actions
            if bool(raw.get("mutation_capable"))!=mutating:
                errors.append(f"adapter_mutation:{aid}")
            if mutating and raw.get("gateway_required") is not True:
                errors.append(f"adapter_gateway:{aid}")
            if raw.get("plan_dispatchable") and raw.get("kind")=="internal_gateway_managed":
                errors.append(f"internal_plan_dispatch:{aid}")
            if raw.get("kind")=="existing_implementation" and not raw.get("implementation"):
                errors.append(f"implementation_missing:{aid}")
        if covered!=set(actions):
            errors.append("adapter_coverage")
        return sorted(set(errors))

    def _collisions(self,candidate:dict[str,Any])->list[str]:
        errors=[]
        eid=candidate["engine_id"]
        if any(e.get("engine_id")==eid for e in self.engine_registry.get("engines",())):
            errors.append(f"ENGINE_ID_COLLISION:{eid}")
        existing_adapter_ids={
            a.get("adapter_id") for a in self.executor_registry_config.get("adapters",())
        }
        for a in candidate.get("adapters",()):
            if a.get("adapter_id") in existing_adapter_ids:
                errors.append(f"ADAPTER_ID_COLLISION:{a.get('adapter_id')}")
        return errors

    def _adapter_descriptors(self,candidate:dict[str,Any])->list[dict[str,Any]]:
        out=[]
        for raw in candidate["adapters"]:
            implementation=raw.get("implementation")
            if raw["kind"]=="internal_gateway_managed":
                implementation="internal.gateway_managed"
            elif raw["kind"]=="callable_scaffold":
                class_name="Generated"+re.sub(r"[^A-Za-z0-9]"," ",raw["adapter_id"]).title().replace(" ","")+"Adapter"
                implementation=f"generated.{_safe(candidate['engine_id']).replace('-','_')}:{class_name}"
            out.append({
                "adapter_id":raw["adapter_id"],
                "status":"ACTIVE",
                "engine_id":candidate["engine_id"],
                "actions":list(raw["actions"]),
                "mutation_capable":bool(raw["mutation_capable"]),
                "gateway_required":bool(raw["gateway_required"]),
                "plan_dispatchable":bool(raw["plan_dispatchable"]),
                "implementation":implementation,
                "priority":int(raw.get("priority",100)),
            })
        return out

    def _engine_entry(self,candidate:dict[str,Any],adapter_ids:list[str])->dict[str,Any]:
        entry={
            "engine_id":candidate["engine_id"],
            "status":"ACTIVE",
            "mutation_capable":bool(candidate["mutation_capable"]),
            "gateway_required":bool(candidate["gateway_required"]),
            "allowed_actions":list(candidate["allowed_actions"]),
            "allowed_domains":list(candidate["allowed_domains"]),
            "executor_adapter_ids":adapter_ids,
        }
        if candidate.get("allowed_path_roots"):
            entry["allowed_path_roots"]=list(candidate["allowed_path_roots"])
        if candidate.get("allowed_exact_paths"):
            entry["allowed_exact_paths"]=list(candidate["allowed_exact_paths"])
        return entry

    def _policy_coverage(self,candidate:dict[str,Any])->list[dict[str,Any]]:
        out=[]
        for p in candidate["action_profiles"]:
            decision=self.decision_engine.evaluate(ActionRequest(
                action=p["action"],
                risk=p["risk"],
                mutating=bool(p["mutating"]),
                domain=p["domain"],
                paths=tuple(candidate.get("allowed_exact_paths",()) or candidate.get("allowed_path_roots",())),
                external_effect=False,
                gates=(),
                actor="autonomy.engine_onboarding",
                metadata={"candidate_engine_id":candidate["engine_id"],"admission_probe":True},
            ))
            out.append({
                "action":p["action"],
                "risk":p["risk"],
                "domain":p["domain"],
                "effect":decision.effect,
                "rule_id":decision.rule_id,
                "execution_authorized":decision.execution_authorized,
                "required_gates":list(decision.required_gates),
                "missing_gates":list(decision.missing_gates),
            })
        return out

    def _scaffold_source(
        self,candidate:dict[str,Any],adapter:dict[str,Any]
    )->tuple[str,str]:
        class_name="Generated"+re.sub(
            r"[^A-Za-z0-9]"," ",adapter["adapter_id"]
        ).title().replace(" ","")+"Adapter"
        filename=_safe(adapter["adapter_id"])+".py"
        source=f'''from __future__ import annotations

class {class_name}:
    # Generated staging scaffold for {candidate["engine_id"]}.
    # This is NOT activated automatically.

    adapter_id = {adapter["adapter_id"]!r}
    engine_id = {candidate["engine_id"]!r}
    actions = {tuple(adapter["actions"])!r}
    mutation_capable = {bool(candidate["mutation_capable"])!r}
    gateway_required = {bool(candidate["gateway_required"])!r}

    def __init__(self, host):
        self.host = host

    def execute(self, ctx):
        raise NotImplementedError(
            "Generated Phase-6 adapter scaffold requires governed implementation"
        )
'''
        return filename,source

    def build_proposal(
        self,candidate:dict[str,Any],*,persist:bool=True
    )->dict[str,Any]:
        semantic_errors=self._semantic_validate(candidate)
        collision_errors=self._collisions(candidate) if candidate.get("engine_id") else []
        candidate_sha=_sha(candidate)

        adapters=self._adapter_descriptors(candidate) if not semantic_errors else []
        engine_entry=self._engine_entry(
            candidate,[x["adapter_id"] for x in adapters]
        ) if not semantic_errors else None

        admission_errors=[*semantic_errors,*collision_errors]
        if not admission_errors:
            try:
                self.phase5_registry.assert_future_engine_admission(
                    engine_entry,adapters
                )
            except Exception as exc:
                admission_errors.append(f"PHASE5_ADMISSION:{type(exc).__name__}:{exc}")

        policy_coverage=self._policy_coverage(candidate) if not semantic_errors else []
        policy_denies=[x["action"] for x in policy_coverage if x["effect"]=="DENY"]

        generated=[]
        scaffold_required=False
        if not admission_errors:
            for raw in candidate["adapters"]:
                if raw["kind"]=="callable_scaffold":
                    scaffold_required=True
                    filename,source=self._scaffold_source(candidate,raw)
                    generated.append({
                        "adapter_id":raw["adapter_id"],
                        "relative_path":f"generated/{_safe(candidate['engine_id'])}/{filename}",
                        "sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),
                        "source":source,
                        "activation_ready":False,
                    })

        if admission_errors:
            activation_status="BLOCKED_ADMISSION"
        elif policy_denies:
            activation_status="BLOCKED_POLICY_COVERAGE"
        elif scaffold_required:
            activation_status="SCAFFOLD_IMPLEMENTATION_REQUIRED"
        else:
            activation_status="GOVERNED_INSTALL_REQUIRED"

        proposal={
            "schema":"PHOENIX_ENGINE_ONBOARDING_PROPOSAL_V1",
            "proposal_id":"ENGPROP-"+uuid.uuid4().hex[:16].upper(),
            "timestamp":int(time.time()),
            "candidate_sha256":candidate_sha,
            "engine_id":candidate.get("engine_id"),
            "engine_registry_patch":engine_entry,
            "executor_registry_patch":adapters,
            "policy_coverage":policy_coverage,
            "generated_scaffolds":[
                {k:v for k,v in item.items() if k!="source"} for item in generated
            ],
            "admission":{
                "status":"PASS" if not admission_errors else "FAIL",
                "errors":admission_errors,
                "phase5_registry_validation":not admission_errors,
                "capability_discovery_code_loaded":False,
            },
            "activation":{
                "status":activation_status,
                "automatic_activation":False,
                "repository_write_performed":False,
                "governed_install_required":activation_status in {
                    "GOVERNED_INSTALL_REQUIRED","SCAFFOLD_IMPLEMENTATION_REQUIRED"
                },
                "policy_denied_actions":policy_denies,
            }
        }
        unsigned=dict(proposal)
        proposal["hmac_sha256"]=self._sign(unsigned)

        if persist:
            proposal_path=self._write_runtime(
                rel_path=f"proposals/{proposal['proposal_id']}.json",
                obj=proposal,
                action="engine.onboarding.proposal.write",
                gates=("audit_log","onboarding_integrity"),
            )
            proposal["runtime_path"]=str(proposal_path)
            for item in generated:
                self._write_text_runtime(
                    rel_path=item["relative_path"],
                    text=item["source"],
                    action="engine.adapter.scaffold.write",
                    gates=("audit_log","onboarding_integrity","admission_tests_pass"),
                )
        return proposal
