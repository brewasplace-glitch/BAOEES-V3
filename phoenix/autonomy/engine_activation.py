from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import subprocess
import time
import uuid

from .adapter_implementation import AdapterImplementationValidator
from .approval_resume import LocalIntegrityKey
from .decision_engine import PolicyDecisionLog
from .engine_onboarding import EngineOnboardingService
from .executor_adapter_registry import UniversalCapabilityExecutorRegistry
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway


def _canonical(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _json_text(obj:Any)->str:
    return json.dumps(obj,indent=2,ensure_ascii=False)+"\n"


def _bump_patch(version:str)->str:
    parts=str(version).split(".")
    if len(parts)!=3 or any(not x.isdigit() for x in parts):
        raise ValueError(f"semantic version required: {version}")
    return f"{parts[0]}.{parts[1]}.{int(parts[2])+1}"


def _norm(path:str)->str:
    return str(path).replace("\\","/").lstrip("./")


class EngineActivationService:
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
        self.policy=json.loads((cfg/"engine_activation_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.engine_registry=json.loads((cfg/"engine_registry_v1.json").read_text(encoding="utf-8-sig"))
        self.executor_registry=json.loads((cfg/"capability_executor_registry_v1.json").read_text(encoding="utf-8-sig"))
        self.bundle_manifest=json.loads((cfg/"policy_bundle_manifest_v1.json").read_text(encoding="utf-8-sig"))
        if gateway is None:
            gateway=UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(self.runtime_root/"policy_decisions"/"decisions_v1.jsonl"),
                audit_log=GatewayAuditLog(self.runtime_root/"gateway"/"audit_v1.jsonl"),
            )
        self.gateway=gateway
        self.onboarding=EngineOnboardingService(self.repo_root,self.runtime_root,gateway=gateway)
        self.validator=AdapterImplementationValidator(self.policy)
        self.integrity_key=LocalIntegrityKey(
            self.runtime_root/"integrity"/"engine_activation_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self):
        if self.policy.get("schema")!="PHOENIX_ENGINE_ACTIVATION_POLICY_V1":
            raise RuntimeError("engine activation policy schema invalid")
        if self.policy.get("status")!="ACTIVE" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("engine activation must be active and fail closed")
        if self.policy["implementation"].get("candidate_code_execution_during_validation") is not False:
            raise RuntimeError("candidate execution during validation must remain disabled")
        if self.policy["governed_install"].get("explicit_approval_required") is not True:
            raise RuntimeError("activation approval invariant missing")

    def _git(self,*args:str,required:bool=True)->str:
        cp=subprocess.run(
            ["git","-c","core.longpaths=true","-C",str(self.repo_root),*args],
            text=True,encoding="utf-8",errors="strict",
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        )
        if cp.returncode:
            if required:
                raise RuntimeError(cp.stdout.rstrip())
            return "UNAVAILABLE"
        return cp.stdout.rstrip("\r\n")

    def _sign(self,obj:dict[str,Any])->str:
        return hmac.new(self.integrity_key,_canonical(obj),hashlib.sha256).hexdigest()

    def verify_signed_transaction(self,obj:dict[str,Any])->bool:
        supplied=str(obj.get("hmac_sha256",""))
        unsigned=dict(obj); unsigned.pop("hmac_sha256",None)
        return bool(supplied) and hmac.compare_digest(supplied,self._sign(unsigned))

    def _runtime_write_json(self,rel:str,obj:dict[str,Any],action:str,gates:tuple[str,...])->Path:
        rel=_norm(rel); uri=f"runtime://engine_activation/{rel}"
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.engine_activation",action=action,risk="LOW",domain="activation",
            paths=(uri,),gates=gates,metadata={"artifact":rel,"sha256":_sha_bytes(_canonical(obj))}
        ))
        self.gateway.consume(permit,engine_id="autonomy.engine_activation",action=action,paths=(uri,))
        path=self.runtime_root/"engine_activation"/Path(rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(_json_text(obj),encoding="utf-8",newline="\n")
        os.replace(tmp,path)
        return path

    def _runtime_write_text(self,rel:str,text:str,action:str,gates:tuple[str,...])->Path:
        rel=_norm(rel); uri=f"runtime://engine_activation/{rel}"
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.engine_activation",action=action,risk="LOW",domain="activation",
            paths=(uri,),gates=gates,metadata={"artifact":rel,"sha256":_sha_bytes(text.encode("utf-8"))}
        ))
        self.gateway.consume(permit,engine_id="autonomy.engine_activation",action=action,paths=(uri,))
        path=self.runtime_root/"engine_activation"/Path(rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(text,encoding="utf-8",newline="\n")
        os.replace(tmp,path)
        return path

    def load_phase6_proposal(self,proposal_path:Path)->dict[str,Any]:
        path=Path(proposal_path).resolve()
        allowed=(self.runtime_root/"engine_onboarding"/"proposals").resolve()
        try:
            same_parent=os.path.samefile(path.parent,allowed)
        except OSError:
            same_parent=False
        if not same_parent:
            try:
                path.relative_to(allowed)
            except ValueError as exc:
                raise PermissionError("proposal must reside in Phase-6 runtime proposal directory") from exc
        obj=json.loads(path.read_text(encoding="utf-8-sig"))
        if obj.get("schema")!="PHOENIX_ENGINE_ONBOARDING_PROPOSAL_V1":
            raise PermissionError("proposal schema invalid")
        if not self.onboarding.verify_signed_artifact(obj):
            raise PermissionError("Phase-6 proposal HMAC verification failed")
        return obj

    def _proposal_gate_errors(self,proposal:dict[str,Any])->list[str]:
        errors=[]
        if proposal.get("admission",{}).get("status")!="PASS":
            errors.append("PHASE6_ADMISSION_NOT_PASS")
        if proposal.get("activation",{}).get("automatic_activation") is not False:
            errors.append("PHASE6_AUTOMATIC_ACTIVATION_BOUNDARY_INVALID")
        denied=proposal.get("activation",{}).get("policy_denied_actions",[]) or []
        if denied:
            errors.append("POLICY_DENIED_ACTIONS:"+",".join(sorted(str(x) for x in denied)))
        eid=proposal.get("engine_id")
        if any(e.get("engine_id")==eid for e in self.engine_registry.get("engines",())):
            errors.append(f"ENGINE_ID_COLLISION:{eid}")
        existing={a.get("adapter_id") for a in self.executor_registry.get("adapters",())}
        for a in proposal.get("executor_registry_patch",()):
            if a.get("adapter_id") in existing:
                errors.append(f"ADAPTER_ID_COLLISION:{a.get('adapter_id')}")
        return errors

    def _proposed_registries(
        self,
        proposal:dict[str,Any],
        validations:dict[str,Any],
    )->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
        engine=json.loads(json.dumps(self.engine_registry))
        executor=json.loads(json.dumps(self.executor_registry))
        manifest=json.loads(json.dumps(self.bundle_manifest))

        engine["version"]=_bump_patch(engine["version"])
        executor["version"]=_bump_patch(executor["version"])
        manifest["version"]=_bump_patch(manifest["version"])
        manifest["engine_registry_version"]=engine["version"]
        manifest["capability_executor_registry_version"]=executor["version"]

        engine_entry=json.loads(json.dumps(proposal["engine_registry_patch"]))
        new_adapters=[]
        for raw in proposal.get("executor_registry_patch",()):
            item=json.loads(json.dumps(raw))
            val=validations.get(item["adapter_id"])
            if val is not None:
                item["implementation"]=f"{val.module_path}:{val.class_name}"
                item["implementation_sha256"]=val.source_sha256
            new_adapters.append(item)

        engine["engines"].append(engine_entry)
        executor["adapters"].extend(new_adapters)
        UniversalCapabilityExecutorRegistry(executor,engine)

        engine_text=_json_text(engine)
        executor_text=_json_text(executor)
        manifest["files"]["engine_registry_v1.json"]["sha256"]=_sha_bytes(engine_text.encode("utf-8"))
        manifest["files"]["capability_executor_registry_v1.json"]["sha256"]=_sha_bytes(executor_text.encode("utf-8"))
        material=json.dumps(manifest["files"],sort_keys=True,separators=(",",":")).encode("utf-8")
        manifest["bundle_sha256"]=_sha_bytes(material)
        return engine,executor,manifest

    def build_transaction(
        self,
        proposal_path:Path,
        implementations:dict[str,Path],
        *,
        persist:bool=True,
    )->dict[str,Any]:
        proposal=self.load_phase6_proposal(proposal_path)
        errors=self._proposal_gate_errors(proposal)
        validations={}
        missing=[]
        generated_ids={x.get("adapter_id") for x in proposal.get("generated_scaffolds",())}

        for descriptor in proposal.get("executor_registry_patch",()):
            if not descriptor.get("plan_dispatchable"):
                continue
            adapter_id=descriptor["adapter_id"]
            if adapter_id in generated_ids or str(descriptor.get("implementation","")).startswith("generated."):
                path=implementations.get(adapter_id)
                if path is None:
                    missing.append(adapter_id)
                    continue
                source=Path(path).read_text(encoding="utf-8-sig")
                val=self.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
                validations[adapter_id]=val
                if not val.activation_ready:
                    errors.extend(f"IMPLEMENTATION:{adapter_id}:{x}" for x in val.errors)
            else:
                # v1 only activates newly generated code when a source hash is explicitly approved.
                errors.append(f"EXISTING_IMPLEMENTATION_ACTIVATION_NOT_SUPPORTED_V1:{adapter_id}")

        planned_files={}
        engine=executor=manifest=None
        if not errors and not missing:
            engine,executor,manifest=self._proposed_registries(proposal,validations)
            for val in validations.values():
                planned_files[val.target_path]=val.source
            planned_files["configs/phoenix/engine_registry_v1.json"]=_json_text(engine)
            planned_files["configs/phoenix/capability_executor_registry_v1.json"]=_json_text(executor)
            planned_files["configs/phoenix/policy_bundle_manifest_v1.json"]=_json_text(manifest)

        if errors:
            status="BLOCKED"
        elif missing:
            status="IMPLEMENTATION_REQUIRED"
        else:
            status="READY_FOR_GOVERNED_INSTALL"

        baseline=self._git("rev-parse","HEAD",required=False)
        tx={
            "schema":"PHOENIX_ENGINE_ACTIVATION_TRANSACTION_V1",
            "transaction_id":"ENGACT-"+uuid.uuid4().hex[:16].upper(),
            "created_at":int(time.time()),
            "baseline":baseline,
            "branch":self._git("branch","--show-current",required=False),
            "proposal_id":proposal["proposal_id"],
            "proposal_sha256":_sha_bytes(_canonical(proposal)),
            "engine_id":proposal["engine_id"],
            "status":status,
            "errors":sorted(set(errors)),
            "missing_implementations":sorted(missing),
            "implementation_sha256":{
                aid:val.source_sha256 for aid,val in sorted(validations.items())
            },
            "implementation_contracts":{
                aid:val.contract() for aid,val in sorted(validations.items())
            },
            "planned_paths":sorted(planned_files),
            "approval_required":True,
            "automatic_activation":False,
            "policy_denied_actions":proposal.get("activation",{}).get("policy_denied_actions",[]),
        }
        tx["hmac_sha256"]=self._sign(dict(tx))

        if persist:
            self._runtime_write_json(
                f"transactions/{tx['transaction_id']}.json",tx,
                "engine.activation.transaction.write",("audit_log","activation_integrity")
            )
            if status=="READY_FOR_GOVERNED_INSTALL":
                bundle_rel=f"bundles/{tx['transaction_id']}"
                hashes={}
                for rel,text in planned_files.items():
                    self._runtime_write_text(
                        f"{bundle_rel}/repo_files/{rel}",text,
                        "engine.activation.bundle.write",
                        ("audit_log","activation_integrity","implementation_validation")
                    )
                    hashes[rel]=_sha_bytes(text.encode("utf-8"))
                bundle_manifest={
                    "schema":"PHOENIX_ENGINE_ACTIVATION_BUNDLE_V1",
                    "transaction_id":tx["transaction_id"],
                    "baseline":baseline,
                    "engine_id":proposal["engine_id"],
                    "files":hashes,
                    "implementation_sha256":tx["implementation_sha256"],
                }
                bundle_manifest["hmac_sha256"]=self._sign(dict(bundle_manifest))
                bundle_path=self._runtime_write_json(
                    f"{bundle_rel}/bundle_manifest.json",bundle_manifest,
                    "engine.activation.bundle.write",
                    ("audit_log","activation_integrity","implementation_validation")
                )
                tx["bundle_dir"]=str(bundle_path.parent)
        return tx

    def verify_bundle(self,bundle_dir:Path)->dict[str,Any]:
        bundle=Path(bundle_dir).resolve()
        manifest_path=bundle/"bundle_manifest.json"
        if not manifest_path.is_file():
            raise PermissionError("activation bundle manifest missing")
        bm=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        supplied=str(bm.get("hmac_sha256","")); unsigned=dict(bm); unsigned.pop("hmac_sha256",None)
        if not supplied or not hmac.compare_digest(supplied,self._sign(unsigned)):
            raise PermissionError("activation bundle HMAC invalid")
        for rel,digest in bm.get("files",{}).items():
            path=bundle/"repo_files"/Path(rel)
            if not path.is_file() or _sha_bytes(path.read_bytes())!=digest:
                raise PermissionError(f"activation bundle file integrity failed: {rel}")
        tx_path=self.runtime_root/"engine_activation"/"transactions"/(bm["transaction_id"]+".json")
        tx=json.loads(tx_path.read_text(encoding="utf-8-sig"))
        if not self.verify_signed_transaction(tx):
            raise PermissionError("activation transaction HMAC invalid")
        if tx.get("status")!="READY_FOR_GOVERNED_INSTALL":
            raise PermissionError("activation transaction not ready")
        if sorted(tx.get("planned_paths",()))!=sorted(bm.get("files",{})):
            raise PermissionError("activation planned path binding mismatch")
        return {"transaction":tx,"bundle_manifest":bm,"bundle_dir":str(bundle)}

    def apply_bundle(
        self,
        bundle_dir:Path,
        backup_receipt:Path,
        approved_implementation_sha256:set[str],
        *,
        explicit_approval:bool,
    )->dict[str,Any]:
        if explicit_approval is not True:
            raise PermissionError("explicit activation approval required")
        verified=self.verify_bundle(bundle_dir)
        tx=verified["transaction"]; bm=verified["bundle_manifest"]
        head=self._git("rev-parse","HEAD")
        branch=self._git("branch","--show-current")
        origin=self._git("rev-parse",f"origin/{branch}")
        if head!=tx["baseline"] or origin!=head:
            raise PermissionError("activation baseline/remote binding mismatch")
        if self._git("status","--porcelain=v1","--untracked-files=all"):
            raise PermissionError("activation requires clean repository")

        receipt=json.loads(Path(backup_receipt).read_text(encoding="utf-8-sig"))
        if receipt.get("status")!="PASS" or receipt.get("baseline")!=head:
            raise PermissionError("verified backup receipt baseline mismatch")
        if receipt.get("bundle_verified") is not True or receipt.get("snapshot_verified") is not True:
            raise PermissionError("verified backup evidence incomplete")

        required=set(str(x).lower() for x in tx.get("implementation_sha256",{}).values())
        approved=set(str(x).lower() for x in approved_implementation_sha256)
        if required!=approved:
            raise PermissionError("approved implementation SHA set does not exactly match transaction")

        paths=tuple(_norm(x) for x in tx["planned_paths"])
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.engine_activation",
            action="engine.activation.repository.apply",
            risk="MEDIUM",domain="activation",paths=paths,
            gates=(
                "human_approval","verified_backup","implementation_validation",
                "exact_scope","policy_bundle_integrity","audit_log"
            ),
            metadata={"transaction_id":tx["transaction_id"],"engine_id":tx["engine_id"]},
        ))
        self.gateway.consume(
            permit,engine_id="autonomy.engine_activation",
            action="engine.activation.repository.apply",paths=paths
        )

        self.update_transaction_status(tx["transaction_id"],"ACTIVATION_IN_PROGRESS",{
            "apply_started_at":int(time.time()),"backup_receipt":str(Path(backup_receipt))
        })

        repo_files=Path(bundle_dir)/"repo_files"
        for rel in paths:
            source=repo_files/Path(rel)
            destination=self.repo_root/Path(rel)
            destination.parent.mkdir(parents=True,exist_ok=True)
            tmp=destination.with_suffix(destination.suffix+".phase7.tmp")
            tmp.write_bytes(source.read_bytes())
            os.replace(tmp,destination)
        return {
            "schema":"PHOENIX_ENGINE_ACTIVATION_APPLY_RESULT_V1",
            "transaction_id":tx["transaction_id"],"engine_id":tx["engine_id"],
            "baseline":head,"planned_paths":list(paths),"status":"ACTIVATION_IN_PROGRESS",
        }

    def smoke_import_activated_adapter(self,transaction_id:str)->dict[str,Any]:
        import importlib
        importlib.invalidate_caches()
        path=self.runtime_root/"engine_activation"/"transactions"/(transaction_id+".json")
        tx=json.loads(path.read_text(encoding="utf-8-sig"))
        if not self.verify_signed_transaction(tx):
            raise PermissionError("activation transaction HMAC invalid")
        if tx.get("status")!="ACTIVATION_IN_PROGRESS":
            raise PermissionError("activation transaction must be in progress for smoke import")
        registry=UniversalCapabilityExecutorRegistry.from_repo(self.repo_root,host=object())
        executor=json.loads((self.repo_root/"configs/phoenix/capability_executor_registry_v1.json").read_text(encoding="utf-8-sig"))
        checked=[]
        for descriptor in executor.get("adapters",()):
            if descriptor.get("engine_id")!=tx.get("engine_id") or descriptor.get("plan_dispatchable") is not True:
                continue
            for action in descriptor.get("actions",()):
                resolved=registry.resolve(tx["engine_id"],action)
                if resolved is None:
                    raise RuntimeError(f"activated adapter resolution failed: {action}")
                desc,adapter=resolved
                if getattr(adapter,"adapter_id",None)!=desc.adapter_id:
                    raise RuntimeError("activated adapter identity mismatch")
                checked.append({"action":action,"adapter_id":desc.adapter_id})
        if not checked:
            raise RuntimeError("activated engine has no plan-dispatch adapter to smoke import")
        return {"schema":"PHOENIX_ENGINE_ACTIVATION_SMOKE_IMPORT_V1","status":"PASS","engine_id":tx["engine_id"],"checked":checked}

    def update_transaction_status(self,transaction_id:str,status:str,extra:dict[str,Any]|None=None)->dict[str,Any]:
        path=self.runtime_root/"engine_activation"/"transactions"/(transaction_id+".json")
        tx=json.loads(path.read_text(encoding="utf-8-sig"))
        if not self.verify_signed_transaction(tx):
            raise PermissionError("activation transaction HMAC invalid")
        tx["status"]=status; tx["updated_at"]=int(time.time())
        if extra: tx.update(extra)
        tx.pop("hmac_sha256",None); tx["hmac_sha256"]=self._sign(dict(tx))
        self._runtime_write_json(
            f"transactions/{transaction_id}.json",tx,
            "engine.activation.transaction.write",("audit_log","activation_integrity")
        )
        return tx
