"""BB24 self-test runner."""

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

from phoenix.construction_planning import (
    ConstructionPlanningEngine,
    ConstructionPlanningExporter,
)


def sample_activities() -> list[dict]:
    return [
        {
            "activity_id": "ACT-001",
            "name": "Site establishment",
            "wbs_code": "01.1",
            "discipline": "construction",
            "duration_workdays": 3,
            "resource_requirements": {
                "site_crew": 5,
                "excavator": 1,
            },
            "direct_cost": 15000,
            "source_object_ids": ["SITE-001"],
        },
        {
            "activity_id": "ACT-002",
            "name": "Foundations",
            "wbs_code": "02.1",
            "discipline": "construction",
            "duration_workdays": 8,
            "predecessor_ids": ["ACT-001"],
            "resource_requirements": {
                "concrete_crew": 7,
                "carpentry_crew": 4,
            },
            "direct_cost": 85000,
            "quantity_ids": ["Q-FOUND"],
        },
        {
            "activity_id": "ACT-003",
            "name": "Structural frame",
            "wbs_code": "03.1",
            "discipline": "construction",
            "duration_workdays": 10,
            "predecessor_ids": ["ACT-002"],
            "resource_requirements": {
                "structural_crew": 6,
                "crane": 1,
            },
            "direct_cost": 140000,
            "quantity_ids": ["Q-FRAME"],
        },
        {
            "activity_id": "ACT-004",
            "name": "Envelope",
            "wbs_code": "04.1",
            "discipline": "architecture",
            "duration_workdays": 7,
            "predecessor_ids": ["ACT-003"],
            "resource_requirements": {
                "facade_crew": 5,
            },
            "direct_cost": 60000,
        },
        {
            "activity_id": "ACT-005",
            "name": "Building services",
            "wbs_code": "10.1",
            "discipline": "building_services",
            "duration_workdays": 6,
            "predecessor_ids": ["ACT-003"],
            "resource_requirements": {
                "services_crew": 6,
            },
            "direct_cost": 75000,
        },
        {
            "activity_id": "ACT-006",
            "name": "Completion milestone",
            "wbs_code": "90.1",
            "discipline": "project_controls",
            "duration_workdays": 0,
            "predecessor_ids": ["ACT-004", "ACT-005"],
            "milestone": True,
        },
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    engine = ConstructionPlanningEngine()
    exporter = ConstructionPlanningExporter()
    report = engine.create_plan(
        {
            "project_id": "PHX-BB24-SELFTEST",
            "project_name": "Phoenix BB24 Self-Test Project",
            "currency": "USD",
        },
        activities=sample_activities(),
        coordination_report={
            "project_id": "PHX-BB24-SELFTEST",
            "coordination_passed": True,
        },
        project_start_date="2026-01-05",
        holidays=["2026-01-19"],
    )

    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None
        output_dir = args.output_dir

    paths = exporter.export_all(report, output_dir)

    with zipfile.ZipFile(paths["xlsx"]) as workbook:
        xlsx_names = set(workbook.namelist())
    xlsx_valid = {
        "xl/workbook.xml",
        "xl/styles.xml",
        "xl/worksheets/sheet1.xml",
        "xl/worksheets/sheet2.xml",
        "xl/worksheets/sheet3.xml",
        "xl/worksheets/sheet4.xml",
    }.issubset(xlsx_names)

    with zipfile.ZipFile(paths["dossier"]) as dossier:
        dossier_names = set(dossier.namelist())
    dossier_valid = {
        "construction_schedule.json",
        "construction_schedule.csv",
        "construction_cashflow.csv",
        "construction_resources.csv",
        "construction_schedule.xlsx",
        "construction_schedule_gantt.html",
        "construction_schedule_gantt.svg",
        "checksums.sha256",
        "PACKAGE_README.txt",
    }.issubset(dossier_names)

    checksum_entries = [
        line
        for line in paths["checksums"].read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    passed = (
        report.planning_passed
        and len(report.scenarios) == 3
        and len(report.baseline.activities) == 6
        and report.baseline.project_duration_workdays > 0
        and len(report.baseline.critical_path) >= 4
        and all(path.is_file() for path in paths.values())
        and xlsx_valid
        and dossier_valid
        and len(checksum_entries) == 7
    )

    print(
        json.dumps(
            {
                "status": "PASSED" if passed else "FAILED",
                "build_block": "BB24",
                "version": "1.0.0",
                "project_id": report.project_id,
                "planning_passed": report.planning_passed,
                "scenario_count": len(report.scenarios),
                "baseline_duration_workdays": (
                    report.baseline.project_duration_workdays
                ),
                "baseline_finish_date": (
                    report.baseline.project_finish_date
                ),
                "baseline_direct_cost": (
                    report.baseline.total_direct_cost
                ),
                "critical_path": report.baseline.critical_path,
                "resource_count": len(
                    report.baseline.resource_summary
                ),
                "cashflow_period_count": len(
                    report.baseline.cashflow_by_month
                ),
                "xlsx_structure_valid": xlsx_valid,
                "dossier_structure_valid": dossier_valid,
                "checksum_entry_count": len(checksum_entries),
                "report_fingerprint_sha256": (
                    engine.fingerprint_report(report)
                ),
                "outputs": {
                    key: str(path)
                    for key, path in sorted(paths.items())
                },
            },
            indent=2,
        )
    )

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
