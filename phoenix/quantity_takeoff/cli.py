"""Command-line interface for BB20."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import QuantityTakeoffEngine
from .exporters import QuantityTakeoffExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Phoenix quantity take-off."
    )
    parser.add_argument("--building-model", type=Path, required=True)
    parser.add_argument("--structural-model", type=Path)
    parser.add_argument("--drawing-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _read_optional(path: Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    building = json.loads(args.building_model.read_text(encoding="utf-8"))
    structural = _read_optional(args.structural_model)
    drawings = _read_optional(args.drawing_manifest)

    engine = QuantityTakeoffEngine()
    exporter = QuantityTakeoffExporter()
    report = engine.generate(
        building,
        structural_model=structural,
        drawing_manifest=drawings,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    exporter.export_json(report, args.output_dir / "quantity_takeoff.json")
    exporter.export_csv(report, args.output_dir / "quantity_takeoff.csv")
    exporter.export_xlsx(report, args.output_dir / "quantity_takeoff.xlsx")

    result = {
        "status": "PASSED",
        "project_id": report.project_id,
        "record_count": len(report.records),
        "issue_count": len(report.issues),
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "output_dir": str(args.output_dir),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
