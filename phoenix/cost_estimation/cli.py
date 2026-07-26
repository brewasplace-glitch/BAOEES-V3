"""Command-line interface for BB21."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import CostEstimationEngine
from .exporters import CostEstimateExporter
from .models import CostScenario
from .ratebook import RateBookLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Phoenix cost estimate.")
    parser.add_argument("--quantity-report", type=Path, required=True)
    parser.add_argument("--ratebook", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    quantity_report = json.loads(args.quantity_report.read_text(encoding="utf-8"))
    ratebook = RateBookLoader().load_file(args.ratebook)
    raw_scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    if not isinstance(raw_scenarios, list):
        raise ValueError("Scenario file must contain a JSON list.")
    scenarios = tuple(CostScenario(**item) for item in raw_scenarios)

    engine = CostEstimationEngine()
    exporter = CostEstimateExporter()
    report = engine.estimate(quantity_report, ratebook, scenarios)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    exporter.export_json(report, args.output_dir / "cost_estimate.json")
    exporter.export_csv(report, args.output_dir / "cost_estimate.csv")
    exporter.export_xlsx(report, args.output_dir / "cost_estimate.xlsx")

    print(
        json.dumps(
            {
                "status": "PASSED",
                "project_id": report.project_id,
                "scenario_count": len(report.scenarios),
                "issue_count": len(report.issues),
                "report_fingerprint_sha256": engine.fingerprint_report(report),
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
