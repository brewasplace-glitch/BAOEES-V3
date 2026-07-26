"""BB22 self-test runner."""

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

from phoenix.bim_coordination import (
    BimCoordinationEngine,
    BimCoordinationExporter,
)


def architecture() -> dict:
    return {
        "project_id": "PHX-BB22-SELFTEST",
        "elements": [
            {
                "id": "DOOR-001",
                "category": "door",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [2.0, 0.0, 0.0, 3.0, 0.3, 2.1]
                },
            },
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [0.0, 0.0, 0.0, 5.0, 0.2, 3.0]
                },
            },
        ],
    }


def structure() -> dict:
    return {
        "project_id": "PHX-BB22-SELFTEST",
        "structural_elements": [
            {
                "id": "BEAM-001",
                "category": "beam",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [2.2, 0.0, 1.8, 4.0, 0.4, 2.3]
                },
            },
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "bbox": [0.0, 0.0, 0.0, 5.1, 0.2, 3.0]
                },
            },
        ],
    }


def quantities() -> dict:
    return {
        "records": [
            {
                "quantity_id": "Q-DOOR",
                "source_object_id": "DOOR-001",
            },
            {
                "quantity_id": "Q-BEAM",
                "source_object_id": "BEAM-001",
            },
            {
                "quantity_id": "Q-WALL",
                "source_object_id": "WALL-001",
            },
        ]
    }


def costs() -> dict:
    return {
        "items": [
            {
                "cost_item_id": "C-DOOR",
                "quantity_id": "Q-DOOR",
            },
            {
                "cost_item_id": "C-BEAM",
                "quantity_id": "Q-BEAM",
            },
        ]
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    engine = BimCoordinationEngine()
    exporter = BimCoordinationExporter()
    report = engine.coordinate(
        {
            "architecture": architecture(),
            "structure": structure(),
        },
        quantity_report=quantities(),
        cost_report=costs(),
    )

    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None
        output_dir = args.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = exporter.export_json(
        report,
        output_dir / "bb22_coordination.json",
    )
    csv_path = exporter.export_csv(
        report,
        output_dir / "bb22_issues.csv",
    )
    xlsx_path = exporter.export_xlsx(
        report,
        output_dir / "bb22_issues.xlsx",
    )
    bcf_path = exporter.export_bcfzip(
        report,
        output_dir / "bb22_issues.bcfzip",
    )

    with zipfile.ZipFile(xlsx_path) as workbook:
        xlsx_valid = {
            "xl/workbook.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
        }.issubset(set(workbook.namelist()))

    with zipfile.ZipFile(bcf_path) as bcf:
        bcf_names = set(bcf.namelist())
        bcf_valid = (
            "bcf.version" in bcf_names
            and "project.bcfp" in bcf_names
            and any(name.endswith("/markup.bcf") for name in bcf_names)
        )

    expected_types = {
        "hard_geometric_clash",
        "shared_geometry_drift",
        "quantity_without_cost",
    }
    passed = (
        expected_types.issubset(report.summary_by_type)
        and json_path.is_file()
        and csv_path.is_file()
        and xlsx_path.is_file()
        and bcf_path.is_file()
        and xlsx_valid
        and bcf_valid
    )

    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB22",
        "version": "1.0.0",
        "project_id": report.project_id,
        "coordination_passed": report.coordination_passed,
        "issue_count": len(report.issues),
        "summary_by_type": report.summary_by_type,
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "json_created": json_path.is_file(),
        "csv_created": csv_path.is_file(),
        "xlsx_created": xlsx_path.is_file(),
        "bcfzip_created": bcf_path.is_file(),
        "xlsx_structure_valid": xlsx_valid,
        "bcf_foundation_valid": bcf_valid,
        "output_dir": str(output_dir),
    }
    print(json.dumps(result, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
