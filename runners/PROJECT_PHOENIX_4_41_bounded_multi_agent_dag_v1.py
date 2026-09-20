#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from pathlib import Path

from phoenix.autonomy import BoundedMultiAgentDagService, RuntimeProviderProbe


class _Result:
    def __init__(self, status, result=None, reason=None):
        self.status = status
        self.result = result
        self.reason = reason


class _SelfTestBoundary:
    provider_id = "test.only.phase11.parallel_boundary"
    provider_version = "1.0.0"

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            True,
            True,
            True,
            (),
            {"test_only": True, "network": "none", "repository_mount": False},
        )

    def execute(self, source, request):
        stub = types.ModuleType("phoenix.autonomy.executor_adapters")
        stub.AdapterExecutionResult = _Result
        phoenix = types.ModuleType("phoenix")
        autonomy = types.ModuleType("phoenix.autonomy")
        phoenix.autonomy = autonomy
        autonomy.executor_adapters = stub
        previous = {
            key: sys.modules.get(key)
            for key in ("phoenix", "phoenix.autonomy", "phoenix.autonomy.executor_adapters")
        }
        try:
            sys.modules["phoenix"] = phoenix
            sys.modules["phoenix.autonomy"] = autonomy
            sys.modules["phoenix.autonomy.executor_adapters"] = stub
            namespace = {"__name__": "phoenix_phase11_selftest"}
            exec(compile(source, "phase11_candidate.py", "exec"), namespace, namespace)
            adapter = namespace[request["class_name"]](None)
            first = adapter.execute(None)
            second = adapter.execute(None)
        finally:
            for key, value in previous.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value
        rows = [
            {"status": item.status, "result": item.result, "reason": item.reason}
            for item in (first, second)
        ]
        return {
            "provider": self.probe().to_dict(),
            "boundary_result": {
                "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
                "nonce": request["nonce"],
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "candidate_code_executed": True,
                "results": rows,
            },
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
    parser.add_argument("--policy-root")
    parser.add_argument("--runtime-root")
    parser.add_argument("--expected-baseline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe", action="store_true")
    mode.add_argument("--live-proof", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    policy_root = Path(args.policy_root or repo).resolve()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else (
        Path.home() / ".project-phoenix" / "autonomy" / "phase11"
    )
    service = BoundedMultiAgentDagService(
        repo,
        runtime,
        policy_root=policy_root,
        provider=_SelfTestBoundary() if args.self_test else None,
        enable_gateway=bool(args.live_proof and policy_root == repo),
    )
    if args.probe:
        result = service.probe()
    else:
        if not args.expected_baseline:
            raise SystemExit("--expected-baseline is required for proof modes")
        result = service.run_synthetic_proof(
            args.expected_baseline,
            persist=bool(args.live_proof and policy_root == repo),
        )
        if args.self_test:
            result["test_only"] = True
            result["live_runtime_proof"] = False
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
