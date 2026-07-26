"""Command-line interface for BB22."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import BimCoordinationEngine
from .exporters import BimCoordinationExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coordinate Phoenix discipline models."
    )
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help="Discipline model as NAME=PATH. Repeat for multiple models.",
    )
    parser.add_argument("--quantity-report", type=Path)
    parser.add_argument("--cost-report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tolerance-m", type=float, default=0.001)
    return parser


def _load(path: Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    models: dict[str, dict] = {}
    for item in args.model:
        if "=" not in item:
            raise SystemExit("--model must use NAME=PATH.")
        name, raw_path = item.split("=", 1)
        path = Path(raw_path)
        models[name] = json.loads(path.read_text(encoding="utf-8"))

    engine = BimCoordinationEngine()
    exporter = BimCoordinationExporter()
    report = engine.coordinate(
        models,
        quantity_report=_load(args.quantity_report),
        cost_report=_load(args.cost_report),
        tolerance_m=args.tolerance_m,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    exporter.export_json(
        report,
        args.output_dir / "bim_coordination_report.json",
    )
    exporter.export_csv(
        report,
        args.output_dir / "bim_coordination_issues.csv",
    )
    exporter.export_xlsx(
        report,
        args.output_dir / "bim_coordination_issues.xlsx",
    )
    exporter.export_bcfzip(
        report,
        args.output_dir / "bim_coordination_issues.bcfzip",
    )

    result = {
        "status": "PASSED",
        "project_id": report.project_id,
        "coordination_passed": report.coordination_passed,
        "issue_count": len(report.issues),
        "open_issue_count": report.open_issue_count,
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "output_dir": str(args.output_dir),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
