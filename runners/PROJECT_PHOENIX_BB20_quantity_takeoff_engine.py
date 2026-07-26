"""BB20 self-test runner."""

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

from phoenix.quantity_takeoff import (
    QuantityTakeoffEngine,
    QuantityTakeoffExporter,
)


def build_model() -> dict:
    return {
        "project_id": "PHX-BB20-SELFTEST",
        "schema_version": "phoenix.building-model/1.0",
        "units": "SI",
        "levels": [
            {
                "id": "LVL-00",
                "name": "Ground floor",
                "elevation_m": 0.0,
                "height_m": 3.0,
            }
        ],
        "elements": [
            {
                "id": "WALL-001",
                "category": "wall",
                "level_id": "LVL-00",
                "geometry": {
                    "length_m": 6.0,
                    "height_m": 3.0,
                    "thickness_m": 0.2,
                },
                "material": {"name": "masonry"},
                "drawing_refs": ["A-101"],
            },
            {
                "id": "SLAB-001",
                "category": "slab",
                "level_id": "LVL-00",
                "geometry": {
                    "length_m": 6.0,
                    "width_m": 4.0,
                    "thickness_m": 0.2,
                },
                "material": {"name": "concrete"},
            },
            {
                "id": "DOOR-001",
                "category": "door",
                "level_id": "LVL-00",
                "geometry": {"width_m": 1.0, "height_m": 2.1},
                "material": {"name": "timber"},
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    engine = QuantityTakeoffEngine()
    exporter = QuantityTakeoffExporter()
    report = engine.generate(build_model())

    output_dir = args.output_dir
    if output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = exporter.export_json(report, output_dir / "bb20_qto.json")
    csv_path = exporter.export_csv(report, output_dir / "bb20_qto.csv")
    xlsx_path = exporter.export_xlsx(report, output_dir / "bb20_qto.xlsx")

    with zipfile.ZipFile(xlsx_path) as archive:
        workbook_valid = {
            "xl/workbook.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
        }.issubset(set(archive.namelist()))

    passed = (
        len(report.records) == 9
        and json_path.is_file()
        and csv_path.is_file()
        and xlsx_path.is_file()
        and workbook_valid
    )

    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB20",
        "version": "1.0.0",
        "project_id": report.project_id,
        "record_count": len(report.records),
        "issue_count": len(report.issues),
        "totals_by_unit": report.totals_by_unit,
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "json_created": json_path.is_file(),
        "csv_created": csv_path.is_file(),
        "xlsx_created": xlsx_path.is_file(),
        "xlsx_structure_valid": workbook_valid,
        "output_dir": str(output_dir),
    }
    print(json.dumps(result, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
