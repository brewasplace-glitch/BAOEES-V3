"""Command-line interface for Phoenix Toolchain & Dependency Manager."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .manager import ToolchainDependencyManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect PROJECT-PHOENIX toolchain dependencies."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Display only required dependencies.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manager = ToolchainDependencyManager()
    report = manager.scan()

    data = report.to_dict()
    if args.required_only:
        data["results"] = [
            item for item in data["results"] if bool(item["required"])
        ]

    data["fingerprint_sha256"] = manager.fingerprint(report)
    data["installation_plan"] = manager.create_installation_plan(report)
    print(json.dumps(data, indent=2, sort_keys=True))

    if args.output:
        manager.export_report(report, args.output)

    return 0 if report.required_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
