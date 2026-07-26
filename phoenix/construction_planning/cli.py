"""Command-line interface for BB24."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ConstructionPlanningEngine
from .exporters import ConstructionPlanningExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Phoenix construction schedule."
    )
    parser.add_argument("--project-metadata", type=Path, required=True)
    parser.add_argument("--activities", type=Path)
    parser.add_argument("--quantity-report", type=Path)
    parser.add_argument("--cost-report", type=Path)
    parser.add_argument("--coordination-report", type=Path)
    parser.add_argument("--project-start-date", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load(path: Path | None):
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = ConstructionPlanningEngine()
    exporter = ConstructionPlanningExporter()
    report = engine.create_plan(
        _load(args.project_metadata),
        activities=_load(args.activities),
        quantity_report=_load(args.quantity_report),
        cost_report=_load(args.cost_report),
        coordination_report=_load(args.coordination_report),
        project_start_date=args.project_start_date,
    )
    paths = exporter.export_all(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": "PASSED" if report.planning_passed else "BLOCKED",
                "project_id": report.project_id,
                "baseline_duration_workdays": (
                    report.baseline.project_duration_workdays
                    if report.scenarios
                    else None
                ),
                "baseline_finish_date": (
                    report.baseline.project_finish_date
                    if report.scenarios
                    else None
                ),
                "blocking_issue_count": report.blocking_issue_count,
                "report_fingerprint_sha256": engine.fingerprint_report(report),
                "outputs": {
                    key: str(path)
                    for key, path in sorted(paths.items())
                },
            },
            indent=2,
        )
    )
    return 0 if report.planning_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
