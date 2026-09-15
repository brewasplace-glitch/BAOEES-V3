from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path


def main() -> int:
    ap=argparse.ArgumentParser(description="PHOENIX Autonomy Policy + North Star v1")
    ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX"))
    ap.add_argument("--request",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    repo=args.repo_root.resolve()
    code_root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(code_root))

    from phoenix.autonomy import ActionRequest, AutonomyDecisionEngine, PolicyDecisionLog

    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    log=PolicyDecisionLog(local/"PROJECT-PHOENIX"/"autonomy"/"policy_decisions"/"decisions_v1.jsonl")
    engine=AutonomyDecisionEngine.from_repo(code_root,log)

    if args.self_test:
        cases=[
            ActionRequest("research.inspect","LOW",False,domain="research"),
            ActionRequest(
                "autonomy.self_improvement.low_risk_evidence","LOW",True,
                domain="orchestration",
                paths=("docs/automation/autonomous_generated/self_improvement/policy-smoke.md",),
                gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
            ),
            ActionRequest("source.modify","MEDIUM",True,domain="software",paths=("phoenix/example.py",)),
            ActionRequest("git.force_push","CRITICAL",True,domain="git",flags=("force_push",)),
        ]
        decisions=[engine.evaluate(x).to_dict() for x in cases]
        if decisions[0]["effect"]!="ALLOW" or not decisions[0]["execution_authorized"]:
            raise RuntimeError("read-only ALLOW self-test failed")
        if decisions[1]["effect"]!="ALLOW_WITH_GATES" or not decisions[1]["execution_authorized"]:
            raise RuntimeError("LOW-risk gated self-test failed")
        if decisions[2]["effect"]!="ESCALATE" or decisions[2]["execution_authorized"]:
            raise RuntimeError("source ESCALATE self-test failed")
        if decisions[3]["effect"]!="DENY" or decisions[3]["execution_authorized"]:
            raise RuntimeError("force-push DENY self-test failed")
        print(json.dumps({
            "schema":"PHOENIX_POLICY_NORTH_STAR_SELF_TEST_V1",
            "status":"PASS",
            "north_star_version":engine.north_star["version"],
            "policy_version":engine.policy["version"],
            "policy_bundle_sha256":engine.bundle_sha256,
            "effects":[x["effect"] for x in decisions],
        },indent=2))
        return 0

    if args.request is None:
        raise SystemExit("--request or --self-test is required")
    data=json.loads(args.request.read_text(encoding="utf-8-sig"))
    req=ActionRequest(
        action=str(data["action"]),
        risk=str(data["risk"]),
        mutating=bool(data["mutating"]),
        domain=str(data.get("domain","general")),
        paths=tuple(data.get("paths",())),
        external_effect=bool(data.get("external_effect",False)),
        gates=tuple(data.get("gates",())),
        flags=tuple(data.get("flags",())),
        actor=str(data.get("actor","phoenix")),
        request_id=str(data.get("request_id") or "POLREQ-CLI"),
        metadata=dict(data.get("metadata",{})),
    )
    print(json.dumps(engine.evaluate(req).to_dict(),indent=2,ensure_ascii=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
