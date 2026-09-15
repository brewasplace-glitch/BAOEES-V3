from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import hashlib, hmac, json, os, subprocess, time, uuid
from .approval_resume import ApprovalResumeEngine, LocalIntegrityKey
from .decision_engine import PolicyDecisionLog
from .executor import LowRiskExecutor, LowRiskExecutionPolicy, TextMutation
from .learning import LearningStore
from .models import Task, RiskLevel
from .policy import AutonomyPolicy
from .promoter import LowRiskMainlinePromoter, LowRiskMainlinePromotionPolicy
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway
from .execution_planner import ExecutionPlan, PlanStep

def _canonical(data:dict[str,Any])->bytes:
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def _safe(value:str)->str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in str(value))

class OrchestrationStore:
    def __init__(self,runtime_root:Path,gateway:UniversalAutonomyGateway,key_path:Path|None=None):
        self.runtime_root=Path(runtime_root); self.gateway=gateway
        self.key=LocalIntegrityKey(key_path or self.runtime_root/"integrity"/"orchestration_hmac_v1.key").load_or_create()
    def run_dir(self,plan_id): return self.runtime_root/"orchestration"/_safe(plan_id)
    def state_path(self,plan_id): return self.run_dir(plan_id)/"state.json"
    def _uri(self,plan_id): return f"runtime://orchestration/{_safe(plan_id)}/state.json"
    def _sign(self,obj): return hmac.new(self.key,_canonical(obj),hashlib.sha256).hexdigest()
    def write_state(self,state):
        obj=dict(state); obj.pop("checkpoint_hmac_sha256",None); obj["checkpoint_hmac_sha256"]=self._sign(obj)
        uri=self._uri(obj["plan_id"])
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.execution_orchestrator",action="orchestration.checkpoint.write",
            risk="LOW",domain="orchestration",paths=(uri,),
            gates=("audit_log","checkpoint_integrity"),
            metadata={"run_id":obj["run_id"],"plan_id":obj["plan_id"],"sequence":obj["sequence"]}
        ))
        self.gateway.consume(permit,engine_id="autonomy.execution_orchestrator",action="orchestration.checkpoint.write",paths=(uri,))
        path=self.state_path(obj["plan_id"]); path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(".json.tmp"); tmp.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,path)
        return obj
    def load_state(self,plan_id):
        path=self.state_path(plan_id)
        if not path.is_file(): return None
        obj=json.loads(path.read_text(encoding="utf-8"))
        sig=str(obj.get("checkpoint_hmac_sha256","")); unsigned=dict(obj); unsigned.pop("checkpoint_hmac_sha256",None)
        if not sig or not hmac.compare_digest(sig,self._sign(unsigned)):
            raise PermissionError("orchestration checkpoint HMAC verification failed")
        return obj
    @contextmanager
    def lock(self,plan_id):
        path=self.run_dir(plan_id)/".lock"; path.parent.mkdir(parents=True,exist_ok=True)
        try: fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError as exc: raise RuntimeError("orchestration run already locked") from exc
        try:
            os.write(fd,f"{os.getpid()}\n".encode()); os.close(fd); yield
        finally:
            path.unlink(missing_ok=True)

class ReadOnlyStepExecutor:
    ALLOWED={"research.inspect","planning.analyze","planning.validate","qa.execute","qa.inspect"}
    def __init__(self,repo_root:Path): self.repo_root=Path(repo_root).resolve()
    def _git(self,*args):
        cp=subprocess.run(["git","-c","core.longpaths=true","-C",str(self.repo_root),*args],
                          text=True,encoding="utf-8",errors="strict",stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        return cp.stdout.rstrip("\r\n") if cp.returncode==0 else "UNAVAILABLE"
    def execute(self,step:PlanStep,plan:ExecutionPlan):
        if step.mutating: raise RuntimeError("read-only executor cannot mutate")
        if step.action not in self.ALLOWED: raise PermissionError(f"read-only action not allowlisted: {step.action}")
        out={"schema":"PHOENIX_READ_ONLY_STEP_RESULT_V1","step_id":step.step_id,"action":step.action,
             "status":"PASS","plan_sha256":plan.plan_sha256,"policy_bundle_sha256":plan.policy_bundle_sha256,
             "timestamp":int(time.time()),"arbitrary_shell_executed":False}
        if step.action=="research.inspect":
            out["repo_head"]=self._git("rev-parse","HEAD"); out["repo_branch"]=self._git("branch","--show-current")
        elif step.action=="planning.analyze":
            out["dependency_count"]=len(step.dependencies); out["plan_status"]=plan.status
        elif step.action=="planning.validate":
            out["step_count"]=len(plan.steps); out["topological_order_size"]=len(plan.topological_order)
        else:
            out["integrity_only"]=True
        return out

class AutonomousExecutionOrchestrator:
    TERMINAL_STEP={"COMPLETE","COMPLETE_HUMAN_APPROVED"}
    TERMINAL_RUN={"COMPLETE","BLOCKED","REJECTED","RECOVERY_REQUIRED"}
    def __init__(self,repo_root:Path,runtime_root:Path,gateway=None,approval_engine=None):
        self.repo_root=Path(repo_root).resolve(); self.runtime_root=Path(runtime_root)
        self.policy=json.loads((self.repo_root/"configs/phoenix/execution_orchestrator_policy_v1.json").read_text(encoding="utf-8-sig"))
        if gateway is None:
            gateway=UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(self.runtime_root/"policy_decisions"/"decisions_v1.jsonl"),
                audit_log=GatewayAuditLog(self.runtime_root/"gateway"/"audit_v1.jsonl")
            )
        self.gateway=gateway; self.store=OrchestrationStore(self.runtime_root,gateway)
        self.approvals=approval_engine or ApprovalResumeEngine(self.runtime_root,gateway)
        self.read_only=ReadOnlyStepExecutor(self.repo_root)
        if self.policy.get("status")!="ACTIVE" or self.policy.get("fail_closed") is not True:
            raise RuntimeError("orchestrator policy invalid")
        if self.policy.get("automatic_replay_of_in_progress_mutation") is not False:
            raise RuntimeError("automatic mutation replay must remain disabled")
    def _git(self,*args,required=True):
        cp=subprocess.run(["git","-c","core.longpaths=true","-C",str(self.repo_root),*args],
                          text=True,encoding="utf-8",errors="strict",stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if cp.returncode:
            if required:
                raise RuntimeError(cp.stdout.rstrip())
            return "UNAVAILABLE"
        return cp.stdout.rstrip("\r\n")
    def _new_state(self,plan):
        return {"schema":"PHOENIX_ORCHESTRATION_STATE_V1","run_id":"ORCH-"+uuid.uuid4().hex[:16].upper(),
                "plan_id":plan.plan_id,"plan_sha256":plan.plan_sha256,"policy_bundle_sha256":plan.policy_bundle_sha256,
                "status":"RUNNING","sequence":0,"started_at":int(time.time()),"updated_at":int(time.time()),
                "baseline_head":self._git("rev-parse","HEAD",required=False),
                "step_states":{s.step_id:{"status":"PENDING","attempts":0,"result":None} for s in plan.steps},
                "pause":None,"events":[]}
    def _checkpoint(self,state,event,payload=None):
        state["sequence"]+=1; state["updated_at"]=int(time.time())
        state["events"].append({"sequence":state["sequence"],"event":event,"timestamp":state["updated_at"],"payload":payload or {}})
        if len(state["events"])>int(self.policy["max_resume_events"]): raise RuntimeError("event bound exceeded")
        return self.store.write_state(state)
    def _validate_state(self,state,plan):
        if state["plan_id"]!=plan.plan_id or state["plan_sha256"]!=plan.plan_sha256: raise RuntimeError("resume plan binding mismatch")
        if state["policy_bundle_sha256"]!=plan.policy_bundle_sha256: raise RuntimeError("resume policy binding mismatch")
        bad=[sid for sid,x in state["step_states"].items() if x["status"]=="IN_PROGRESS_MUTATION"]
        if bad:
            state["status"]="RECOVERY_REQUIRED"; state["pause"]={"reason":"MUTATION_IN_PROGRESS_RECONCILIATION_REQUIRED","steps":bad}
            self._checkpoint(state,"RECOVERY_REQUIRED",state["pause"]); return False
        return True
    def _deps_complete(self,step,state):
        return all(state["step_states"][d]["status"] in self.TERMINAL_STEP for d in step.dependencies)
    def _approval(self,step,plan):
        return self.approvals.load_valid_receipt(plan_id=plan.plan_id,plan_sha256=plan.plan_sha256,
            step_id=step.step_id,policy_bundle_sha256=plan.policy_bundle_sha256)
    def _request(self,step,plan,state):
        req=self.approvals.issue_request(plan_id=plan.plan_id,plan_sha256=plan.plan_sha256,
            step_id=step.step_id,policy_bundle_sha256=plan.policy_bundle_sha256,
            action=step.action,risk=step.risk,mutating=step.mutating,
            reason=f"Policy effect ESCALATE via {step.policy_rule_id}")
        state["status"]="PAUSED_APPROVAL"; state["pause"]={"reason":"HUMAN_APPROVAL_REQUIRED","step_id":step.step_id,
            "request_id":req["request_id"],"request_path":str(self.approvals.request_path(plan.plan_id,step.step_id))}
        self._checkpoint(state,"PAUSED_APPROVAL",state["pause"])

    def _content_for(self,step:PlanStep,plan:ExecutionPlan,payloads:dict[str,Any])->str:
        if step.step_id in payloads:
            value=payloads[step.step_id]
            return value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False)+"\n"
        if step.action=="evidence.generate":
            return json.dumps({
                "schema":"PHOENIX_ORCHESTRATED_EVIDENCE_V1",
                "plan_id":plan.plan_id,"plan_sha256":plan.plan_sha256,
                "step_id":step.step_id,"policy_bundle_sha256":plan.policy_bundle_sha256
            },indent=2)+"\n"
        return (
            "# PHOENIX Orchestrated LOW-risk Update\n\n"
            f"- Plan: `{plan.plan_id}`\n"
            f"- Plan SHA256: `{plan.plan_sha256}`\n"
            f"- Step: `{step.step_id}`\n"
            f"- Policy bundle: `{plan.policy_bundle_sha256}`\n"
        )

    def _execute_lowrisk(self,step,plan,state,backup_receipt,payloads):
        if not step.paths: raise RuntimeError("LOW-risk mutation step has no paths")
        if state.get("candidate"): raise RuntimeError("v1 allows one active candidate")
        if state["baseline_head"]=="UNAVAILABLE": raise RuntimeError("mutation requires Git repository baseline")
        self._checkpoint(state,"PRE_MUTATION_CHECKPOINT",{"step_id":step.step_id})
        ss=state["step_states"][step.step_id]
        ss["status"]="IN_PROGRESS_MUTATION"; ss["attempts"]+=1
        self._checkpoint(state,"MUTATION_IN_PROGRESS",{"step_id":step.step_id})
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.low_risk_executor",action=step.action,risk=step.risk,
            domain=step.domain,paths=step.paths,gates=step.proposed_gates,
            metadata={"plan_id":plan.plan_id,"step_id":step.step_id}
        ))
        cfg=self.repo_root/"configs/phoenix"
        executor=LowRiskExecutor(
            self.repo_root,
            AutonomyPolicy.from_json(cfg/"autonomy_policy_v1.json"),
            LowRiskExecutionPolicy.from_json(cfg/"low_risk_execution_policy_v1.json"),
            LearningStore(self.runtime_root/"learning"/"events_v1.jsonl")
        )
        mutations=tuple(TextMutation(path,self._content_for(step,plan,payloads),"replace") for path in step.paths)
        task=Task(
            task_id="ORCH-"+step.step_id,title=step.title,capability_id="AUTO-ORCH-008",
            action="update",paths=step.paths,requested_risk=RiskLevel.LOW,
            metadata={"gateway_action":step.action,"orchestrated":True}
        )
        result=executor.execute(
            task,mutations,expected_head=state["baseline_head"],keep_candidate=True,
            publish_candidate=False,gateway=self.gateway,gateway_permit=permit
        )
        state["candidate"]={
            "candidate_branch":result["candidate_branch"],
            "candidate_commit":result["candidate_commit"],
            "requested_paths":result["requested_paths"],
            "baseline_head":state["baseline_head"]
        }
        ss["status"]="COMPLETE"; ss["result"]=result
        self._checkpoint(state,"LOW_RISK_MUTATION_COMPLETE",{"step_id":step.step_id,"candidate_commit":result["candidate_commit"]})

    def _execute_promotion(self,step,plan,state,backup_receipt):
        candidate=state.get("candidate")
        if not candidate: raise RuntimeError("promotion requires active candidate")
        expected=state["baseline_head"]; branch=candidate["candidate_branch"]
        paths=tuple(x.strip().replace("\\","/") for x in self._git("diff","--name-only",f"{expected}..{branch}").splitlines() if x.strip())
        self._checkpoint(state,"PRE_PROMOTION_CHECKPOINT",{"step_id":step.step_id})
        ss=state["step_states"][step.step_id]
        ss["status"]="IN_PROGRESS_MUTATION"; ss["attempts"]+=1
        self._checkpoint(state,"PROMOTION_IN_PROGRESS",{"step_id":step.step_id})
        permit=self.gateway.authorize(MutationIntent(
            engine_id="autonomy.mainline_promoter",action="git.fast_forward_promotion",
            risk="LOW",domain="git",paths=paths,gates=step.proposed_gates,
            metadata={"plan_id":plan.plan_id,"step_id":step.step_id}
        ))
        cfg=self.repo_root/"configs/phoenix"
        promoter=LowRiskMainlinePromoter(
            self.repo_root,
            LowRiskMainlinePromotionPolicy.from_json(cfg/"low_risk_mainline_promotion_policy_v1.json"),
            runtime_root=self.runtime_root/"promotion"
        )
        result=promoter.promote(
            branch,expected,Path(backup_receipt),gateway=self.gateway,gateway_permit=permit
        )
        ss["status"]="COMPLETE"; ss["result"]=result
        state["candidate"]=None; state["baseline_head"]=result["promoted_commit"]
        self._checkpoint(state,"PROMOTION_COMPLETE",{"step_id":step.step_id,"promoted_commit":result["promoted_commit"]})

    def run(self,plan:ExecutionPlan,*,backup_receipt:Path|None=None,execution_payloads:dict[str,Any]|None=None):
        if len(plan.steps)>int(self.policy["max_steps_per_run"]): raise RuntimeError("step bound exceeded")
        if plan.policy_bundle_sha256!=self.gateway.decision_engine.bundle_sha256: raise RuntimeError("plan policy bundle is stale")
        execution_payloads=execution_payloads or {}
        with self.store.lock(plan.plan_id):
            state=self.store.load_state(plan.plan_id)
            if state is None:
                state=self._new_state(plan); self._checkpoint(state,"RUN_CREATED",{"plan_sha256":plan.plan_sha256})
            if not self._validate_state(state,plan): return state
            if state["status"] in self.TERMINAL_RUN: return state
            state["status"]="RUNNING"; state["pause"]=None; self._checkpoint(state,"RUN_RESUME",{})
            by={s.step_id:s for s in plan.steps}
            for sid in plan.topological_order:
                step=by[sid]; ss=state["step_states"][sid]
                if ss["status"] in self.TERMINAL_STEP: continue
                if not self._deps_complete(step,state): continue
                if step.step_status in {"DENY","DENY_UNREGISTERED_ENGINE"}:
                    state["status"]="BLOCKED"; state["pause"]={"reason":step.step_status,"step_id":sid}
                    self._checkpoint(state,"BLOCKED",state["pause"]); return state
                if step.step_status=="GATED_PENDING":
                    state["status"]="PAUSED_GATES"; state["pause"]={"reason":"MISSING_GATES","step_id":sid,"missing_gates":list(step.missing_gates)}
                    self._checkpoint(state,"PAUSED_GATES",state["pause"]); return state
                if step.step_status=="ESCALATE":
                    rec=self._approval(step,plan)
                    if rec is None: self._request(step,plan,state); return state
                    if rec["decision"]=="DEFER":
                        state["status"]="PAUSED_APPROVAL"; state["pause"]={"reason":"DEFERRED","step_id":sid}
                        self._checkpoint(state,"APPROVAL_DEFERRED",state["pause"]); return state
                    if rec["decision"]=="REJECT":
                        state["status"]="REJECTED"; state["pause"]={"reason":"HUMAN_REJECTED","step_id":sid}
                        self._checkpoint(state,"REJECTED",state["pause"]); return state
                    if step.mutating:
                        state["status"]="WAITING_APPROVED_MUTATION"
                        state["pause"]={"reason":"APPROVED_BUT_EXECUTOR_AND_GATEWAY_STILL_REQUIRED","step_id":sid,
                                        "engine_id":step.engine_id,"action":step.action}
                        self._checkpoint(state,"WAITING_APPROVED_MUTATION",state["pause"]); return state
                    ss["status"]="COMPLETE_HUMAN_APPROVED"; ss["result"]={"approval_receipt_id":rec["receipt_id"]}
                    self._checkpoint(state,"HUMAN_APPROVED_STEP_COMPLETE",{"step_id":sid}); continue
                if step.step_status!="READY":
                    state["status"]="BLOCKED"; state["pause"]={"reason":"UNKNOWN_STEP_STATUS","step_id":sid}
                    self._checkpoint(state,"BLOCKED",state["pause"]); return state
                if step.mutating:
                    if backup_receipt is None:
                        state["status"]="PAUSED_GATES"
                        state["pause"]={"reason":"BACKUP_RECEIPT_REQUIRED_FOR_MUTATION","step_id":sid}
                        self._checkpoint(state,"PAUSED_GATES",state["pause"]); return state
                    if step.engine_id=="autonomy.low_risk_executor" and step.action in {"documentation.update","evidence.generate"}:
                        self._execute_lowrisk(step,plan,state,Path(backup_receipt),execution_payloads)
                        continue
                    if step.engine_id=="autonomy.mainline_promoter" and step.action=="git.fast_forward_promotion":
                        self._execute_promotion(step,plan,state,Path(backup_receipt))
                        continue
                    state["status"]="WAITING_EXECUTOR"
                    state["pause"]={"reason":"NO_SAFE_DISPATCHER_FOR_READY_MUTATION","step_id":sid,
                                    "engine_id":step.engine_id,"action":step.action}
                    self._checkpoint(state,"WAITING_EXECUTOR",state["pause"]); return state
                ss["status"]="IN_PROGRESS_READ_ONLY"; ss["attempts"]+=1
                self._checkpoint(state,"READ_ONLY_STEP_START",{"step_id":sid})
                ss["result"]=self.read_only.execute(step,plan); ss["status"]="COMPLETE"
                self._checkpoint(state,"READ_ONLY_STEP_COMPLETE",{"step_id":sid})
            incomplete=[sid for sid,x in state["step_states"].items() if x["status"] not in self.TERMINAL_STEP]
            if incomplete:
                state["status"]="WAITING_EXECUTOR"; state["pause"]={"reason":"DEPENDENCY_WAIT","steps":incomplete}
                self._checkpoint(state,"WAITING_EXECUTOR",state["pause"]); return state
            state["status"]="COMPLETE"; state["pause"]=None; self._checkpoint(state,"RUN_COMPLETE",{})
            return state
