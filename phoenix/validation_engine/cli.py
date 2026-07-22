"""CLI for Phoenix Validation Engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import PhoenixValidationEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Phoenix Validation Engine")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    report = PhoenixValidationEngine().run(
        project_id=str(config["project_id"]),
        repo_root=Path(args.repo_root).resolve(),
        required_paths=tuple(config.get("required_paths", [])),
        json_paths=tuple(config.get("json_paths", [])),
        import_modules=tuple(config.get("import_modules", [])),
        release_manifest=config.get("release_manifest"),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
