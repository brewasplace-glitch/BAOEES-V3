"""Command-line interface for Phoenix Release Manager v2.3."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from phoenix.updater.release_manager import ReleaseManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m phoenix.release",
        description="Build a Phoenix release package.",
    )
    parser.add_argument("--name", default="project-phoenix")
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--file",
        action="append",
        dest="files",
        help="Repository-relative file to include. Repeat as needed.",
    )
    parser.add_argument("--changelog", default="")
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root. Defaults to the current directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    manager = ReleaseManager(Path(arguments.repository_root))
    result = manager.create_release(
        name=arguments.name,
        version=arguments.version,
        relative_paths=arguments.files,
        changelog=arguments.changelog,
    )
    print(manager.to_json(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())