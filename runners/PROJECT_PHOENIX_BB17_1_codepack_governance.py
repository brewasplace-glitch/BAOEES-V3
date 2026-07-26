"""BB17.1 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.codepack_governance import CodepackGovernanceEngine, CodepackRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    registry = CodepackRegistry()
    governance = CodepackGovernanceEngine()
    manifests = registry.load_directory(ROOT / "configs/phoenix/codepacks/registry")
    governance.ensure_single_active(manifests)
    decisions = [
        governance.activation_decision(item, as_of_date="2026-07-26").to_dict()
        for item in manifests
    ]

    if args.output:
        registry.export_index(manifests, args.output)

    result = {
        "status": "PASSED",
        "build_block": "BB17.1",
        "version": "1.0.0",
        "codepack_count": len(manifests),
        "eligible_count": sum(1 for item in decisions if item["eligible"]),
        "registry_fingerprint_sha256": registry.fingerprint(manifests),
        "report_created": bool(args.output and args.output.is_file()),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
