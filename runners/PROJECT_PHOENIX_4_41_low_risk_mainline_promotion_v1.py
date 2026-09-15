from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(
        description="PHOENIX LOW-risk backup-gated mainline promotion v1"
    )
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--candidate-branch",required=True)
    ap.add_argument("--expected-head",required=True)
    ap.add_argument("--backup-receipt",type=Path,required=True)
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    code_root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(code_root))

    from phoenix.autonomy import LowRiskMainlinePromotionPolicy, LowRiskMainlinePromoter

    policy_path=code_root/"configs/phoenix/low_risk_mainline_promotion_policy_v1.json"
    if not policy_path.is_file():
        raise RuntimeError(f"promotion policy missing: {policy_path}")

    policy=LowRiskMainlinePromotionPolicy.from_json(policy_path)
    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    promoter=LowRiskMainlinePromoter(
        repo,policy,local/"PROJECT-PHOENIX"/"autonomy"/"mainline_promotion"
    )
    result=promoter.promote(
        args.candidate_branch,args.expected_head,args.backup_receipt
    )
    print(json.dumps(result,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
