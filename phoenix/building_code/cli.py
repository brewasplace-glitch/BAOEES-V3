"""Command-line interface for BB17."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import BuildingCodeEngine
from .registry import CodeProfileRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    model = json.loads(args.model.read_text(encoding="utf-8"))
    profile = CodeProfileRegistry().load_file(args.profile)
    engine = BuildingCodeEngine()
    report = engine.evaluate(model, profile)
    data = report.to_dict(profile.fail_severities)
    data["report_fingerprint_sha256"] = engine.fingerprint_report(report, profile)
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    if args.output:
        engine.export_report(report, profile, args.output)
    return 0 if report.is_compliant_for(profile.fail_severities) else 3


if __name__ == "__main__":
    raise SystemExit(main())
