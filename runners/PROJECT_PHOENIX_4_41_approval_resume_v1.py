from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 approval decision / resume receipt v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--plan-id",required=True)
    ap.add_argument("--step-id",required=True)
    ap.add_argument("--decision",required=True,choices=["APPROVE","REJECT","DEFER"])
    ap.add_argument("--reason",default="")
    ap.add_argument("--runtime-root",type=Path)
    args=ap.parse_args()
    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))
    from phoenix.autonomy import ApprovalResumeEngine, GatewayAuditLog, PolicyDecisionLog, UniversalAutonomyGateway

    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    runtime=args.runtime_root or (local/"PROJECT-PHOENIX"/"autonomy")
    gateway=UniversalAutonomyGateway.from_repo(
        repo,
        decision_log=PolicyDecisionLog(runtime/"policy_decisions"/"decisions_v1.jsonl"),
        audit_log=GatewayAuditLog(runtime/"gateway"/"audit_v1.jsonl"),
    )
    receipt=ApprovalResumeEngine(runtime,gateway).record_decision(
        plan_id=args.plan_id,step_id=args.step_id,decision=args.decision,
        reason=args.reason,actor="human"
    )
    print(json.dumps(receipt,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
