"""Command-line interface for the Phoenix Development Kit."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .doctor import Doctor
from .runner import run_tests
from .sync import Synchronizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pdk",
        description="Phoenix Development Kit",
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="PROJECT-PHOENIX repository root.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Diagnose the repository.")
    subparsers.add_parser("sync", help="Synchronize required directories.")
    subparsers.add_parser("test", help="Run the repository test suite.")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    root = Path(arguments.repository_root)

    if arguments.command == "doctor":
        report = Doctor(root).run()
        print(report.to_json())
        return 0 if report.status == "PASS" else 1

    if arguments.command == "sync":
        result = Synchronizer(root).run()
        print(result.to_json())
        return 0 if result.status == "PASS" else 1

    if arguments.command == "test":
        result = run_tests(root)
        print(result.to_json())
        return result.returncode

    return 2


if __name__ == "__main__":
    sys.exit(main())