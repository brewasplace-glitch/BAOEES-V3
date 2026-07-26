"""Command-line interface for BB25."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import ProcurementTenderingEngine
from .exporters import ProcurementTenderingExporter


def _load(path: Path | None, default):
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phoenix procurement and tender outputs.")
    parser.add_argument("--project-metadata", type=Path, required=True)
    parser.add_argument("--quantity-report", type=Path, required=True)
    parser.add_argument("--cost-report", type=Path, required=True)
    parser.add_argument("--planning-report", type=Path, required=True)
    parser.add_argument("--coordination-report", type=Path, required=True)
    parser.add_argument("--suppliers", type=Path)
    parser.add_argument("--bids", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    engine = ProcurementTenderingEngine()
    report = engine.create_procurement(
        _load(args.project_metadata, {}),
        quantity_report=_load(args.quantity_report, {}),
        cost_report=_load(args.cost_report, {}),
        planning_report=_load(args.planning_report, {}),
        coordination_report=_load(args.coordination_report, {}),
        suppliers=_load(args.suppliers, []),
        bids=_load(args.bids, []),
    )
    paths = ProcurementTenderingExporter().export_all(report, args.output_dir)
    print(json.dumps({
        "status": "PASSED" if report.procurement_passed else "BLOCKED",
        "project_id": report.project_id,
        "currency": report.currency,
        "package_count": len(report.packages),
        "bid_count": len(report.bids),
        "recommendation_count": len(report.recommendations),
        "blocking_issue_count": report.blocking_issue_count,
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "outputs": {key: str(value) for key, value in sorted(paths.items())},
    }, indent=2))
    return 0 if report.procurement_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
