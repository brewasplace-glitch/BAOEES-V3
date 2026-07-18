from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.updater import PhoenixUpdater
from phoenix.updater.package_builder import PackageBuilder


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m phoenix.updater")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")
    sub.add_parser("update")

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("package")

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("package")
    apply_parser.add_argument("--no-tests", action="store_true")
    apply_parser.add_argument("--commit", action="store_true")
    apply_parser.add_argument("--push", action="store_true")

    build = sub.add_parser("build")
    build.add_argument("--id", required=True, dest="update_id")
    build.add_argument("--version", required=True)
    build.add_argument("--description", required=True)
    build.add_argument("--file", action="append", required=True, dest="files")
    build.add_argument("--test", action="append", default=[])
    build.add_argument("--commit-message", required=True)
    build.add_argument("--no-push", action="store_true")
    build.add_argument("--overwrite", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    root = find_root()
    updater = PhoenixUpdater(root)

    if args.command == "list":
        result = {
            "engine": "Phoenix Updater",
            "version": updater.VERSION,
            "packages": [path.name for path in updater.discover()],
            "status": "PASS",
        }
    elif args.command == "update":
        result = updater.apply_next(run_tests=True, commit=True, push=True)
    elif args.command == "inspect":
        result = updater.inspect((root / args.package).resolve())
    elif args.command == "apply":
        result = updater.apply(
            (root / args.package).resolve(),
            run_tests=not args.no_tests,
            commit=args.commit,
            push=args.push,
        )
    else:
        commands = [
            value.strip().split()
            for value in args.test
            if value.strip()
        ]
        package = PackageBuilder(root).build(
            update_id=args.update_id,
            version=args.version,
            description=args.description,
            source_files=args.files,
            test_commands=commands,
            commit_message=args.commit_message,
            auto_push=not args.no_push,
            overwrite=args.overwrite,
        )
        result = {
            "engine": "Phoenix Package Builder",
            "version": updater.VERSION,
            "package": str(package),
            "status": "PASS",
        }

    print(json.dumps(result, ensure_ascii=True, indent=2))

    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
