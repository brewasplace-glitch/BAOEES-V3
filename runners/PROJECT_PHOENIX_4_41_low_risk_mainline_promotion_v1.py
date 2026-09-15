from __future__ import annotations
import argparse, json, os, sys, subprocess
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

    from phoenix.autonomy import (
        LowRiskMainlinePromotionPolicy, LowRiskMainlinePromoter,
        UniversalAutonomyGateway, MutationIntent, PolicyDecisionLog, GatewayAuditLog,
    )

    policy_path=code_root/"configs/phoenix/low_risk_mainline_promotion_policy_v1.json"
    if not policy_path.is_file():
        raise RuntimeError(f"promotion policy missing: {policy_path}")

    policy=LowRiskMainlinePromotionPolicy.from_json(policy_path)
    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    decision_log=PolicyDecisionLog(
        local/"PROJECT-PHOENIX"/"autonomy"/"policy_decisions"/"decisions_v1.jsonl"
    )
    gateway=UniversalAutonomyGateway.from_repo(
        code_root,
        decision_log=decision_log,
        audit_log=GatewayAuditLog(
            local/"PROJECT-PHOENIX"/"autonomy"/"universal_gateway"/"audit_v1.jsonl"
        ),
    )
    promoter=LowRiskMainlinePromoter(
        repo,policy,local/"PROJECT-PHOENIX"/"autonomy"/"mainline_promotion"
    )
    # Candidate paths are validated by the promoter; the permit is bound to the
    # exact diff paths before the merge itself.
    candidate=args.candidate_branch
    diff=subprocess.run(
        ["git","-c","core.longpaths=true","-C",str(repo),"diff","--name-only",f"{args.expected_head}..{candidate}"],
        text=True,encoding="utf-8",errors="strict",
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True,
    ).stdout.splitlines()
    permit=gateway.authorize(MutationIntent(
        engine_id="autonomy.mainline_promoter",
        action="git.fast_forward_promotion",
        risk="LOW",
        domain="git",
        paths=tuple(x.strip().replace("\\","/") for x in diff if x.strip()),
        gates=(
            "verified_backup","candidate_validated","tests_pass","evidence_pass",
            "ff_only","normal_non_force_push","remote_race_guard","audit_log",
        ),
    ))
    result=promoter.promote(
        args.candidate_branch,args.expected_head,args.backup_receipt,
        gateway=gateway,gateway_permit=permit,
    )
    print(json.dumps(result,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
