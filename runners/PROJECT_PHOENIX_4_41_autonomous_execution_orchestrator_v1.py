from __future__ import annotations
import argparse, json, os, sys, tempfile
from pathlib import Path

def default_goal():
    return {
        "schema":"PHOENIX_GOAL_SPEC_V1","goal_id":"PHASE4-READONLY-PROBE",
        "objective":"Execute a bounded read-only plan durably and prove restart-safe checkpointing.",
        "goal_type":"generic.analysis","domain":"planning",
        "success_criteria":["all read-only steps complete"],"constraints":["no mutation"],
        "available_gates":[],"context":{},"subgoals":[]
    }

def main():
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 autonomous execution orchestrator v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--goal-file",type=Path)
    ap.add_argument("--runtime-root",type=Path)
    ap.add_argument("--backup-receipt",type=Path)
    ap.add_argument("--payload-file",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))
    from phoenix.autonomy import GoalSpec, AutonomousExecutionPlanner, AutonomousExecutionOrchestrator

    raw=json.loads(args.goal_file.read_text(encoding="utf-8-sig")) if args.goal_file else default_goal()
    plan=AutonomousExecutionPlanner(repo).plan(GoalSpec.from_dict(raw))
    if args.runtime_root:
        runtime=args.runtime_root
    elif args.self_test:
        runtime=Path(tempfile.mkdtemp(prefix="phoenix_phase4_probe_"))
    else:
        local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
        runtime=local/"PROJECT-PHOENIX"/"autonomy"

    payloads={}
    if args.payload_file:
        payloads=json.loads(args.payload_file.read_text(encoding="utf-8-sig"))
    orch=AutonomousExecutionOrchestrator(repo,runtime)
    state=orch.run(plan,backup_receipt=args.backup_receipt,execution_payloads=payloads)
    if args.self_test:
        if state["status"]!="COMPLETE":
            raise RuntimeError(f"expected COMPLETE, got {state['status']}")
        again=orch.run(plan)
        if again["status"]!="COMPLETE":
            raise RuntimeError("restart/resume failed")
        state["self_test"]="PASS"; state["restart_resume"]="PASS"
    print(json.dumps(state,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
