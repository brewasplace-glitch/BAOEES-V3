from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(
        description="PHOENIX 4.41 bounded LOW-risk self-improvement loop v1"
    )
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--expected-head",required=True)
    ap.add_argument("--backup-receipt",type=Path,required=True)
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    code_root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(code_root))

    from phoenix.autonomy import (
        AutonomyPolicy,
        LowRiskExecutionPolicy,
        LowRiskMainlinePromotionPolicy,
        LowRiskSelfImprovementPolicy,
        LowRiskSelfImprovementLoop,
        OpenSourceScout,
        LearningStore,
    )

    cfg=code_root/"configs/phoenix"
    autonomy=AutonomyPolicy.from_json(cfg/"autonomy_policy_v1.json")
    execution=LowRiskExecutionPolicy.from_json(cfg/"low_risk_execution_policy_v1.json")
    promotion=LowRiskMainlinePromotionPolicy.from_json(
        cfg/"low_risk_mainline_promotion_policy_v1.json"
    )
    self_policy=LowRiskSelfImprovementPolicy.from_json(
        cfg/"self_improvement_policy_v1.json"
    )
    scout=OpenSourceScout.from_json(cfg/"autonomy_open_source_catalog_v1.json")

    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    learning=LearningStore(
        local/"PROJECT-PHOENIX"/"autonomy"/"learning"/"events_v1.jsonl"
    )

    loop=LowRiskSelfImprovementLoop(
        repo,
        autonomy,
        execution,
        promotion,
        self_policy,
        scout,
        learning,
        runtime_root=local/"PROJECT-PHOENIX"/"autonomy"/"self_improvement",
    )
    result=loop.run_once(args.expected_head,args.backup_receipt)
    print(json.dumps(result,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
