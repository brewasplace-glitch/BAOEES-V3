from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

def main() -> int:
    ap=argparse.ArgumentParser(description="PHOENIX 4.41 Phase 2 Universal Autonomy Gateway self-test")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    args=ap.parse_args()
    root=args.repo_root.resolve()
    sys.path.insert(0,str(root))

    from phoenix.autonomy import (
        GatewayAuditLog, MutationIntent, PolicyDecisionLog, UniversalAutonomyGateway
    )

    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    gateway=UniversalAutonomyGateway.from_repo(
        root,
        decision_log=PolicyDecisionLog(
            local/"PROJECT-PHOENIX"/"autonomy"/"policy_decisions"/"decisions_v1.jsonl"
        ),
        audit_log=GatewayAuditLog(
            local/"PROJECT-PHOENIX"/"autonomy"/"universal_gateway"/"audit_v1.jsonl"
        ),
    )

    denied_unregistered=False
    try:
        gateway.authorize(MutationIntent(
            engine_id="future.unregistered.engine",
            action="documentation.update",
            risk="LOW",
            domain="documentation",
            paths=("docs/automation/autonomous_generated/future.md",),
            gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
        ))
    except PermissionError:
        denied_unregistered=True

    if not denied_unregistered:
        raise RuntimeError("unregistered future engine was not denied")

    permit=gateway.authorize(MutationIntent(
        engine_id="autonomy.low_risk_executor",
        action="documentation.update",
        risk="LOW",
        domain="documentation",
        paths=("docs/automation/autonomous_generated/gateway_probe.md",),
        gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
    ))
    gateway.consume(
        permit,
        engine_id="autonomy.low_risk_executor",
        action="documentation.update",
        paths=("docs/automation/autonomous_generated/gateway_probe.md",),
    )

    reuse_denied=False
    try:
        gateway.consume(
            permit,
            engine_id="autonomy.low_risk_executor",
            action="documentation.update",
            paths=("docs/automation/autonomous_generated/gateway_probe.md",),
        )
    except PermissionError:
        reuse_denied=True
    if not reuse_denied:
        raise RuntimeError("one-time permit reuse was not denied")

    out={
        "schema":"PHOENIX_UNIVERSAL_AUTONOMY_GATEWAY_SELF_TEST_V1",
        "status":"PASS",
        "policy_version":gateway.decision_engine.policy["version"],
        "north_star_version":gateway.decision_engine.north_star["version"],
        "policy_bundle_sha256":gateway.decision_engine.bundle_sha256,
        "future_unregistered_engine":"DENY",
        "registered_engine_permit":"PASS",
        "permit_one_time_use":"PASS",
        "all_future_mutation_engines":"REGISTER_AND_GATEWAY_REQUIRED",
    }
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
