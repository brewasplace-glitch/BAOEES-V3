from __future__ import annotations

from pathlib import Path
import argparse
import json
import tempfile

from phoenix.autonomy import AdapterSynthesisService


def _candidate() -> dict:
    return {
        "schema": "PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id": "future.phase8.selftest",
        "display_name": "Phase 8 Self Test",
        "mutation_capable": False,
        "gateway_required": False,
        "allowed_actions": ["research.inspect"],
        "allowed_domains": ["research"],
        "action_profiles": [
            {
                "action": "research.inspect",
                "risk": "LOW",
                "domain": "research",
                "mutating": False,
                "plan_dispatchable": True,
            }
        ],
        "adapters": [
            {
                "adapter_id": "future.phase8.selftest.adapter",
                "actions": ["research.inspect"],
                "kind": "callable_scaffold",
                "mutation_capable": False,
                "gateway_required": False,
                "plan_dispatchable": True,
                "priority": 100,
            }
        ],
        "metadata": {"self_test": True},
    }


def self_test(repo_root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="phoenix_phase8_") as td:
        service = AdapterSynthesisService(repo_root, Path(td))
        proposal = service.onboarding.build_proposal(_candidate(), persist=True)
        adapter_id = proposal["executor_registry_patch"][0]["adapter_id"]
        candidate = service.build_candidate(
            Path(proposal["runtime_path"]), adapter_id, persist=True
        )
        attestation = service.verify_candidate(
            Path(candidate["runtime_path"]), persist=True
        )
        handoff = service.promote_candidate(
            Path(attestation["runtime_path"]),
            candidate["source_sha256"],
            explicit_approval=True,
            persist=True,
        )
        return {
            "schema": "PHOENIX_PHASE8_SELF_TEST_V1",
            "status": "PASS",
            "synthesis_status": candidate["status"],
            "verification_status": attestation["status"],
            "handoff_status": handoff["status"],
            "candidate_code_executed": attestation["candidate_code_executed"],
            "repository_write_performed": handoff["repository_write_performed"],
            "automatic_activation": handoff["automatic_activation"],
            "phase7_activation_transaction_eligible": handoff[
                "phase7_activation_transaction_eligible"
            ],
            "provider": attestation["isolation"]["provider_id"],
            "source_sha256": candidate["source_sha256"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PROJECT PHOENIX Phase 8 adapter synthesis and verification"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--adapter-id")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--attestation", type=Path)
    parser.add_argument("--approve-sha256")
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    if args.self_test:
        print(json.dumps(self_test(repo), indent=2, ensure_ascii=False))
        return 0
    if args.runtime_root is None:
        parser.error("--runtime-root is required outside --self-test")

    service = AdapterSynthesisService(repo, args.runtime_root)
    if args.proposal and args.adapter_id:
        result = service.build_candidate(args.proposal, args.adapter_id, persist=True)
    elif args.candidate:
        result = service.verify_candidate(args.candidate, persist=True)
    elif args.attestation and args.approve_sha256:
        result = service.promote_candidate(
            args.attestation,
            args.approve_sha256,
            explicit_approval=True,
            persist=True,
        )
    else:
        parser.error(
            "choose --proposal + --adapter-id, --candidate, or --attestation + --approve-sha256"
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
