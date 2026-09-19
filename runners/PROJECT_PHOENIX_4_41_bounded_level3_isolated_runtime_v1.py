from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from phoenix.autonomy import (
    AdapterSynthesisService,
    BoundedLevel3CycleService,
    RuntimeProviderProbe,
)


class SelfTestBoundaryProvider:
    provider_id = "test.only.simulated_boundary"
    provider_version = "1.0.0"

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            True,
            True,
            True,
            (),
            {"test_only": True, "live_runtime_proof": False},
        )

    def execute(self, source, request):
        result = {
            "adapter_id": request["adapter_id"],
            "engine_id": request["engine_id"],
            "action": request["action"],
            "mode": "READ_ONLY_SYNTHESIZED_V1",
        }
        boundary = {
            "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
            "nonce": request["nonce"],
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "candidate_code_executed": True,
            "results": [
                {"status": "COMPLETE", "result": result, "reason": None},
                {"status": "COMPLETE", "result": result, "reason": None},
            ],
        }
        return {
            "provider": self.probe().to_dict(),
            "boundary_result": boundary,
            "exit_code": 0,
            "elapsed_seconds": 0.0,
            "timed_out": False,
            "stdout_sha256": hashlib.sha256(b"self-test").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "command_policy": {"test_only": True},
        }


def proof_candidate():
    return {
        "schema": "PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id": "future.phase9.proof",
        "display_name": "Phase 9 Runtime Proof",
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
                "adapter_id": "future.phase9.proof.adapter",
                "actions": ["research.inspect"],
                "kind": "callable_scaffold",
                "mutation_capable": False,
                "gateway_required": False,
                "plan_dispatchable": True,
                "priority": 100,
            }
        ],
        "metadata": {"phase9_proof": True},
    }


def build_candidate(repo_root: Path, runtime_root: Path):
    synthesis = AdapterSynthesisService(repo_root, runtime_root)
    proposal = synthesis.onboarding.build_proposal(proof_candidate(), persist=True)
    adapter_id = proposal["executor_registry_patch"][0]["adapter_id"]
    return synthesis.build_candidate(
        Path(proposal["runtime_path"]), adapter_id, persist=True
    )


def run_self_test(repo_root: Path):
    with tempfile.TemporaryDirectory(prefix="phoenix_phase9_selftest_") as td:
        runtime = Path(td)
        candidate = build_candidate(repo_root, runtime)
        service = BoundedLevel3CycleService(
            repo_root, runtime, provider=SelfTestBoundaryProvider()
        )
        attestation = service.execute_candidate(
            Path(candidate["runtime_path"]), "research.inspect"
        )
        return {
            "schema": "PHOENIX_PHASE9_SELF_TEST_V1",
            "status": "PASS",
            "test_only": True,
            "live_runtime_proof": False,
            "simulated_boundary": True,
            "policy_and_attestation_flow": attestation["status"],
            "repository_write_performed": attestation["repository_write_performed"],
            "automatic_activation": attestation["automatic_activation"],
        }


def run_live_proof(repo_root: Path, runtime_root: Path):
    candidate = build_candidate(repo_root, runtime_root)
    service = BoundedLevel3CycleService(repo_root, runtime_root)
    probe = service.probe()
    if not probe["execution_enabled"]:
        raise RuntimeError(
            "PHASE9_LIVE_RUNTIME_PROVIDER_UNAVAILABLE:" + ",".join(probe["reasons"])
        )
    attestation = service.execute_candidate(
        Path(candidate["runtime_path"]), "research.inspect"
    )
    return {
        "schema": "PHOENIX_PHASE9_LIVE_PROOF_RESULT_V1",
        "status": "PASS",
        "test_only": False,
        "live_runtime_proof": True,
        "provider_id": attestation["provider"]["provider_id"],
        "candidate_code_executed": attestation["execution"]["candidate_code_executed"],
        "deterministic_runtime_replay": attestation["deterministic_runtime_replay"],
        "repository_write_performed": attestation["repository_write_performed"],
        "repository_commit_created": attestation["repository_commit_created"],
        "repository_push_performed": attestation["repository_push_performed"],
        "automatic_activation": attestation["automatic_activation"],
        "governed_phase7_handoff_eligible": attestation["governed_phase7_handoff_eligible"],
        "attestation_path": attestation["runtime_path"],
        "attestation_sha256": attestation["attestation_sha256"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runtime-root")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--probe", action="store_true")
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--live-proof", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    runtime_root = Path(args.runtime_root).resolve() if args.runtime_root else (
        Path(tempfile.gettempdir()) / "PROJECT-PHOENIX" / "phase9_runtime"
    )
    if args.probe:
        result = BoundedLevel3CycleService(repo_root, runtime_root).probe()
    elif args.self_test:
        result = run_self_test(repo_root)
    else:
        result = run_live_proof(repo_root, runtime_root)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
