from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_DEFAULT=Path(r"C:\PROJECT-PHOENIX")
EXPECTED_BASELINE="e897e302431d09e85341dcb9dc5279671bd0f61a"

def main():
    ap=argparse.ArgumentParser(description="PROJECT PHOENIX 4.41 autonomous development foundation")
    ap.add_argument("--repo-root",type=Path,default=REPO_DEFAULT)
    ap.add_argument("--mode",choices=["dry-run","low-risk-auto"],default="dry-run")
    ap.add_argument("--task-title",default="Advance PHOENIX autonomous development foundation")
    ap.add_argument("--action",default="plan")
    ap.add_argument("--path",action="append",default=[])
    ap.add_argument("--output-dir",type=Path)
    ap.add_argument("--expected-head",default=None)
    ap.add_argument("--allowed-dirty-path",action="append",default=[])
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))

    from phoenix.autonomy import (
        AutonomyPolicy, OpenSourceScout, LearningStore, AutonomousCycle,
        CycleMode, Task
    )
    from phoenix.autonomy.dashboard import render_dashboard

    policy=AutonomyPolicy.from_json(repo/"configs/phoenix/autonomy_policy_v1.json")
    scout=OpenSourceScout.from_json(repo/"configs/phoenix/autonomy_open_source_catalog_v1.json")

    out=args.output_dir
    if out is None:
        local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
        out=local/"PROJECT-PHOENIX"/"autonomy"
    out.mkdir(parents=True,exist_ok=True)

    learning=LearningStore(out/"learning_events_v1.jsonl")
    cycle=AutonomousCycle(repo,policy,scout,learning)

    task=Task(
        task_id="AUTO-FOUNDATION-DRYRUN-001",
        title=args.task_title,
        capability_id="AUTO-CYCLE-001",
        action=args.action,
        paths=tuple(args.path),
    )
    mode=CycleMode(args.mode)
    report=cycle.run(
        task,
        mode,
        expected_head=args.expected_head,
        allowed_dirty_paths=tuple(args.allowed_dirty_path),
    )

    report_path=out/"latest_cycle_report_v1.json"
    dashboard_path=out/"autonomy_dashboard_v1.html"
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    render_dashboard(report,dashboard_path)

    print(json.dumps({
        "status":"PASS" if report["gate"]["passed"] else "BLOCKED",
        "mode":report["mode"],
        "mutation_performed":report["mutation_performed"],
        "risk":report["decision"]["risk"],
        "allowed":report["decision"]["allowed"],
        "gate_passed":report["gate"]["passed"],
        "report":str(report_path),
        "dashboard":str(dashboard_path),
    },indent=2,ensure_ascii=True))
    return 0 if report["gate"]["passed"] else 2

if __name__=="__main__":
    raise SystemExit(main())
