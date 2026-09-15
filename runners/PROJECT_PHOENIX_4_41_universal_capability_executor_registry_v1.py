from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 universal capability executor registry v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    sys.path.insert(0,str(repo))
    from phoenix.autonomy import UniversalCapabilityExecutorRegistry

    reg=UniversalCapabilityExecutorRegistry.from_repo(repo,host=object())
    report=reg.coverage_report()

    samples={}
    for engine,action in [
        ("autonomy.execution_planner","research.inspect"),
        ("autonomy.low_risk_executor","documentation.update"),
        ("autonomy.mainline_promoter","git.fast_forward_promotion"),
    ]:
        resolved=reg.resolve(engine,action)
        samples[f"{engine}:{action}"]=resolved[0].adapter_id if resolved else None

    report["sample_plan_adapters"]=samples
    report["unknown_future_action"]=(
        "DENY_NO_REGISTERED_ADAPTER"
        if reg.resolve("future.unknown","future.action") is None
        else "UNEXPECTEDLY_RESOLVED"
    )
    report["internal_bib_plan_dispatch"]=(
        "DENY"
        if reg.resolve("bib.auto_sync","bib.auto_sync") is None
        else "UNEXPECTEDLY_RESOLVED"
    )

    if args.self_test:
        if not report["complete"]:
            raise RuntimeError("executor registry coverage incomplete")
        if report["unknown_future_action"]!="DENY_NO_REGISTERED_ADAPTER":
            raise RuntimeError("future action default did not fail closed")
        if report["internal_bib_plan_dispatch"]!="DENY":
            raise RuntimeError("internal adapter leaked into plan dispatch")
        if not all(report["sample_plan_adapters"].values()):
            raise RuntimeError("built-in plan adapter sample missing")
        report["self_test"]="PASS"

    print(json.dumps(report,indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
