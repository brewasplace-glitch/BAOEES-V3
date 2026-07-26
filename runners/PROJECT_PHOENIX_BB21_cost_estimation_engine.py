"""BB21 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from phoenix.cost_estimation import (
    CostEstimateExporter,
    CostEstimationEngine,
    CostScenario,
    RateBookLoader,
)


def quantity_report() -> dict:
    return {
        "project_id": "PHX-BB21-SELFTEST",
        "schema_version": "phoenix.quantity-takeoff-report/1.0",
        "records": [
            {
                "quantity_id": "QTO-WALL-VOLUME",
                "source_object_id": "WALL-001",
                "source_model": "building_model",
                "source_level_id": "LVL-00",
                "category": "wall",
                "work_section": "04 Walls and partitions",
                "material": "masonry",
                "quantity_type": "wall_volume",
                "value": 3.0,
                "unit": "m3",
                "drawing_refs": ["A-101"],
                "metadata": {},
            },
            {
                "quantity_id": "QTO-SLAB-VOLUME",
                "source_object_id": "SLAB-001",
                "source_model": "structural_model",
                "source_level_id": "LVL-00",
                "category": "slab",
                "work_section": "05 Floors and slabs",
                "material": "concrete",
                "quantity_type": "slab_volume",
                "value": 4.0,
                "unit": "m3",
                "drawing_refs": ["S-101"],
                "metadata": {},
            },
            {
                "quantity_id": "QTO-DOOR-COUNT",
                "source_object_id": "DOOR-001",
                "source_model": "building_model",
                "source_level_id": "LVL-00",
                "category": "door",
                "work_section": "07 Doors",
                "material": "timber",
                "quantity_type": "count",
                "value": 2.0,
                "unit": "ea",
                "drawing_refs": ["A-201"],
                "metadata": {},
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    ratebook_path = (
        _REPOSITORY_ROOT
        / "configs"
        / "phoenix"
        / "cost_ratebooks"
        / "phoenix_synthetic_test_ratebook_v1_0.json"
    )
    ratebook = RateBookLoader().load_file(ratebook_path)
    scenarios = (
        CostScenario(
            id="SCENARIO-BASE",
            name="Base",
            currency="EUR",
            overhead_percent=10.0,
            risk_percent=5.0,
            contingency_percent=3.0,
            profit_percent=4.0,
        ),
        CostScenario(
            id="SCENARIO-CONSERVATIVE",
            name="Conservative",
            currency="EUR",
            quantity_factor=1.03,
            location_factor=1.05,
            escalation_percent=2.0,
            material_factor=1.04,
            labor_factor=1.06,
            equipment_factor=1.03,
            subcontract_factor=1.05,
            other_factor=1.03,
            overhead_percent=12.0,
            risk_percent=8.0,
            contingency_percent=5.0,
            profit_percent=5.0,
        ),
    )

    engine = CostEstimationEngine()
    exporter = CostEstimateExporter()
    report = engine.estimate(quantity_report(), ratebook, scenarios)

    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None
        output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = exporter.export_json(report, output_dir / "bb21_cost_estimate.json")
    csv_path = exporter.export_csv(report, output_dir / "bb21_cost_estimate.csv")
    xlsx_path = exporter.export_xlsx(report, output_dir / "bb21_cost_estimate.xlsx")

    with zipfile.ZipFile(xlsx_path) as workbook:
        xlsx_valid = {
            "xl/workbook.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
            "xl/worksheets/sheet3.xml",
        }.issubset(set(workbook.namelist()))

    passed = (
        len(report.scenarios) == 2
        and all(len(scenario.lines) == 3 for scenario in report.scenarios)
        and report.scenarios[1].total_cost > report.scenarios[0].total_cost
        and json_path.is_file()
        and csv_path.is_file()
        and xlsx_path.is_file()
        and xlsx_valid
    )

    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB21",
        "version": "1.0.0",
        "project_id": report.project_id,
        "currency": report.currency,
        "price_date": report.price_date,
        "scenario_count": len(report.scenarios),
        "base_total": report.scenarios[0].total_cost,
        "conservative_total": report.scenarios[1].total_cost,
        "issue_count": len(report.issues),
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "json_created": json_path.is_file(),
        "csv_created": csv_path.is_file(),
        "xlsx_created": xlsx_path.is_file(),
        "xlsx_structure_valid": xlsx_valid,
        "output_dir": str(output_dir),
    }
    print(json.dumps(result, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
