from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.updater import PhoenixUpdater


def find_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("PROJECT-PHOENIX repository root niet gevonden.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m phoenix.updater")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("package")

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("package")
    apply_parser.add_argument("--no-tests", action="store_true")
    apply_parser.add_argument("--commit", action="store_true")
    apply_parser.add_argument("--push", action="store_true")

    args = parser.parse_args()
    root = find_root()
    updater = PhoenixUpdater(root)

    if args.command == "list":
        result = {
            "engine": "Phoenix Updater",
            "version": updater.VERSION,
            "packages": [path.name for path in updater.discover()],
            "status": "PASS",
        }
    elif args.command == "inspect":
        result = updater.inspect((root / args.package).resolve())
    else:
        result = updater.apply(
            (root / args.package).resolve(),
            run_tests=not args.no_tests,
            commit=args.commit,
            push=args.push,
        )

    print(json.dumps(result, ensure_ascii=True, indent=2))

    if result.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
