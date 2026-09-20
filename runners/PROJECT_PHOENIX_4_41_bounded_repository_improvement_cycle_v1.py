#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

from phoenix.autonomy import (
    BoundedRepositoryImprovementCycleService,
    RuntimeProviderProbe,
)


class _SelfTestBoundary:
    provider_id = "test.only.phase10.boundary"
    provider_version = "1.0.0"

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            True,
            True,
            True,
            (),
            {"test_only": True, "network": "none"},
        )

    def execute(self, source, request):
        expected_match = re.search(r"^EXPECTED = '([a-f0-9]{64})'$", source, re.MULTILINE)
        lane_match = re.search(r"^LANE = '([^']+)'$", source, re.MULTILINE)
        if not expected_match or not lane_match:
            raise RuntimeError("self-test patch probe source invalid")
        patch_match = re.search(r"^PATCH = base64\.b64decode\('([^']+)'\)$", source, re.MULTILINE)
        if not patch_match:
            raise RuntimeError("self-test patch bytes missing")
        import base64

        patch = base64.b64decode(patch_match.group(1))
        result = {
            "patch_sha256": expected_match.group(1),
            "patch_bytes": len(patch),
            "lane": lane_match.group(1),
            "mode": "PHASE10_READ_ONLY_PATCH_PROBE_V1",
        }
        row = {"status": "COMPLETE", "result": result, "reason": None}
        boundary = {
            "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
            "nonce": request["nonce"],
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "candidate_code_executed": True,
            "results": [row, dict(row)],
        }
        return {
            "provider": self.probe().to_dict(),
            "boundary_result": boundary,
            "exit_code": 0,
            "elapsed_seconds": 0.001,
            "timed_out": False,
            "stdout_sha256": "0" * 64,
            "stderr_sha256": "0" * 64,
            "command_policy": {"network": "none", "test_only": True},
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runtime-root")
    parser.add_argument("--policy-root")
    parser.add_argument("--expected-baseline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--live-proof", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    policy_root = Path(args.policy_root or repo).resolve()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else (
        Path.home() / ".project-phoenix" / "autonomy" / "phase10"
    )
    provider = _SelfTestBoundary() if args.self_test else None
    service = BoundedRepositoryImprovementCycleService(
        repo,
        runtime,
        policy_root=policy_root,
        provider=provider,
        enable_gateway=bool(args.live_proof and policy_root == repo),
    )
    if args.probe:
        result = service.probe()
    else:
        baseline = args.expected_baseline
        if not baseline:
            raise SystemExit("--expected-baseline is required for proof modes")
        result = service.run_synthetic_proof(
            baseline,
            persist=bool(args.live_proof and policy_root == repo),
        )
        if args.self_test:
            result["test_only"] = True
            result["live_runtime_proof"] = False
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
