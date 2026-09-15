from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def default_goal() -> dict:
    return {
        "schema":"PHOENIX_GOAL_SPEC_V1",
        "goal_id":"PHASE3-PROBE",
        "objective":"Build a governed PHOENIX feature without bypassing policy or the universal gateway.",
        "goal_type":"phoenix.feature_build",
        "domain":"software",
        "success_criteria":[
            "plan is a deterministic DAG",
            "every step has a central policy decision",
            "mutations require a registered gateway-aware engine",
            "source changes escalate under current policy"
        ],
        "constraints":["no force push","no gate bypass"],
        "available_gates":[],
        "context":{
            "source_paths":["phoenix/example.py"]
        },
        "subgoals":[]
    }

def main() -> int:
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 autonomous execution planner v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--goal-file",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))

    from phoenix.autonomy import GoalSpec, AutonomousExecutionPlanner, ExecutionCoordinator

    if args.goal_file:
        raw=json.loads(args.goal_file.read_text(encoding="utf-8-sig"))
    else:
        raw=default_goal()

    goal=GoalSpec.from_dict(raw)
    planner=AutonomousExecutionPlanner(repo)
    plan=planner.plan(goal)
    out=plan.to_dict()

    if args.self_test:
        if out["status"]!="HUMAN_DECISION_REQUIRED":
            raise RuntimeError(f"expected source-modification escalation, got {out['status']}")
        source_steps=[x for x in out["steps"] if x["action"]=="source.modify"]
        if len(source_steps)!=1 or source_steps[0]["policy_effect"]!="ESCALATE":
            raise RuntimeError("source.modify policy escalation missing")
        if any(x["mutating"] and not x["gateway_required"] for x in out["steps"]):
            raise RuntimeError("mutation step missing gateway requirement")
        ticketable=ExecutionCoordinator().next_ready(plan,set())
        if not ticketable:
            raise RuntimeError("planner returned no initially-ready step")
        out["self_test"]="PASS"

    print(json.dumps(out,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
