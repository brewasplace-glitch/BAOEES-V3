#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.autonomy.autonomous_build_orchestrator_v1_0 import (
    AutonomousBuildOrchestrator,
    BuildOrchestratorError,
    load_manifest,
    manifest_sha256,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project Phoenix Autonomous Build Orchestrator v1.0"
    )
    parser.add_argument("--repo", default=r"C:\PROJECT-PHOENIX")

    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--manifest", required=True)

    dry = sub.add_parser("dry-run")
    dry.add_argument("--manifest", required=True)

    run = sub.add_parser("run")
    run.add_argument("--manifest", required=True)

    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        orchestrator = AutonomousBuildOrchestrator(args.repo)

        if args.command == "inspect":
            result = {
                "manifest_sha256": manifest_sha256(args.manifest),
                "preflight": orchestrator.preflight(manifest),
                "capability": orchestrator.inspect_capability(manifest),
            }
        else:
            result = orchestrator.run(
                manifest,
                dry_run=(args.command == "dry-run"),
            )
            result["manifest_sha256"] = manifest_sha256(args.manifest)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (BuildOrchestratorError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PHOENIX_AUTONOMOUS_BUILD_ERROR={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
