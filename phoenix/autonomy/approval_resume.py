from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, hmac, json, os, secrets, time, uuid
from .universal_gateway import MutationIntent, UniversalAutonomyGateway

def _canonical(data:dict[str,Any]) -> bytes:
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def _safe(value:str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in str(value))

class LocalIntegrityKey:
    def __init__(self,path:Path):
        self.path=Path(path)

    def _persist_binary(self,data:bytes,mode:str)->None:
        with self.path.open(mode) as handle:
            written=handle.write(data)
            if written!=len(data):
                raise RuntimeError(f"local integrity key short write: {written}/{len(data)}")
            handle.flush()
            os.fsync(handle.fileno())

    def _read_existing(self)->bytes:
        data=self.path.read_bytes()
        if len(data)==32:
            return data
        recovered=data.replace(b"\r\n",b"\n")
        if len(recovered)==32:
            self._persist_binary(recovered,"wb")
            migrated=self.path.read_bytes()
            if migrated!=recovered:
                raise RuntimeError("legacy integrity key migration verification failed")
            return recovered
        raise RuntimeError(f"local integrity key invalid length: {len(data)} bytes")

    def load_or_create(self)->bytes:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            return self._read_existing()
        except FileNotFoundError:
            pass
        data=secrets.token_bytes(32)
        try:
            self._persist_binary(data,"xb")
        except FileExistsError:
            return self._read_existing()
        persisted=self._read_existing()
        if not hmac.compare_digest(persisted,data):
            raise RuntimeError("local integrity key persistence mismatch")
        return persisted


class ApprovalResumeEngine:
    DECISIONS={"APPROVE","REJECT","DEFER"}
    def __init__(self,runtime_root:Path,gateway:UniversalAutonomyGateway,key_path:Path|None=None):
        self.runtime_root=Path(runtime_root); self.gateway=gateway
        self.key=LocalIntegrityKey(key_path or self.runtime_root/"integrity"/"approval_hmac_v1.key").load_or_create()
    def _dir(self,plan_id): return self.runtime_root/"approvals"/_safe(plan_id)
    def request_path(self,plan_id,step_id): return self._dir(plan_id)/(f"{_safe(step_id)}.request.json")
    def receipt_path(self,plan_id,step_id): return self._dir(plan_id)/(f"{_safe(step_id)}.receipt.json")
    def _uri(self,plan_id,step_id,suffix): return f"runtime://approvals/{_safe(plan_id)}/{_safe(step_id)}.{suffix}.json"
    def _sign(self,obj):
        return hmac.new(self.key,_canonical(obj),hashlib.sha256).hexdigest()
    def _verify(self,obj,field="hmac_sha256"):
        supplied=str(obj.get(field,"")); unsigned=dict(obj); unsigned.pop(field,None)
        if not supplied or not hmac.compare_digest(supplied,self._sign(unsigned)):
            raise PermissionError("approval artifact HMAC verification failed")

    def issue_request(self,*,plan_id,plan_sha256,step_id,policy_bundle_sha256,action,risk,mutating,reason):
        path=self.request_path(plan_id,step_id)
        if path.is_file():
            obj=json.loads(path.read_text(encoding="utf-8")); self._verify(obj); return obj
        obj={
            "schema":"PHOENIX_APPROVAL_REQUEST_V1","request_id":"APPREQ-"+uuid.uuid4().hex[:16].upper(),
            "plan_id":plan_id,"plan_sha256":plan_sha256,"step_id":step_id,
            "policy_bundle_sha256":policy_bundle_sha256,"action":action,"risk":risk,
            "mutating":bool(mutating),"reason":reason,"request_nonce":secrets.token_hex(16),
            "timestamp":int(time.time())
        }
        obj["hmac_sha256"]=self._sign(obj)
        uri=self._uri(plan_id,step_id,"request")
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.execution_orchestrator",action="approval.request.write",risk="LOW",
            domain="approval",paths=(uri,),gates=("audit_log","approval_integrity"),
            metadata={"plan_id":plan_id,"step_id":step_id}
        ))
        self.gateway.consume(permit,engine_id="autonomy.execution_orchestrator",action="approval.request.write",paths=(uri,))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
        return obj

    def record_decision(self,*,plan_id,step_id,decision,reason="",actor="human"):
        decision=str(decision).upper()
        if decision not in self.DECISIONS: raise ValueError("decision must be APPROVE, REJECT or DEFER")
        rp=self.request_path(plan_id,step_id)
        if not rp.is_file(): raise RuntimeError("approval request not found")
        req=json.loads(rp.read_text(encoding="utf-8")); self._verify(req)
        obj={
            "schema":"PHOENIX_APPROVAL_RECEIPT_V1","receipt_id":"APPREC-"+uuid.uuid4().hex[:16].upper(),
            "request_id":req["request_id"],"plan_id":req["plan_id"],"plan_sha256":req["plan_sha256"],
            "step_id":req["step_id"],"policy_bundle_sha256":req["policy_bundle_sha256"],
            "decision":decision,"reason":str(reason),"actor":str(actor),
            "request_nonce":req["request_nonce"],"timestamp":int(time.time())
        }
        obj["hmac_sha256"]=self._sign(obj)
        uri=self._uri(plan_id,step_id,"receipt")
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.approval_resume",action="approval.receipt.write",risk="LOW",
            domain="approval",paths=(uri,),gates=("audit_log","approval_integrity"),
            metadata={"plan_id":plan_id,"step_id":step_id,"decision":decision}
        ))
        self.gateway.consume(permit,engine_id="autonomy.approval_resume",action="approval.receipt.write",paths=(uri,))
        path=self.receipt_path(plan_id,step_id); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
        return obj

    def load_valid_receipt(self,*,plan_id,plan_sha256,step_id,policy_bundle_sha256):
        path=self.receipt_path(plan_id,step_id)
        if not path.is_file(): return None
        rec=json.loads(path.read_text(encoding="utf-8")); self._verify(rec)
        if rec.get("plan_id")!=plan_id: raise PermissionError("approval plan binding mismatch")
        if rec.get("plan_sha256")!=plan_sha256: raise PermissionError("approval plan SHA binding mismatch")
        if rec.get("step_id")!=step_id: raise PermissionError("approval step binding mismatch")
        if rec.get("policy_bundle_sha256")!=policy_bundle_sha256: raise PermissionError("approval policy binding mismatch")
        req=json.loads(self.request_path(plan_id,step_id).read_text(encoding="utf-8")); self._verify(req)
        if rec.get("request_nonce")!=req.get("request_nonce"): raise PermissionError("approval nonce mismatch")
        return rec
