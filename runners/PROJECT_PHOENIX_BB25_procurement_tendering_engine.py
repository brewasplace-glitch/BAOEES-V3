"""BB25 self-test runner."""

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

from phoenix.procurement_tendering import (
    ProcurementTenderingEngine,
    ProcurementTenderingExporter,
)


def source_data() -> dict:
    project_id = "PHX-BB25-SELFTEST"
    return {
        "metadata": {
            "project_id": project_id,
            "project_name": "Phoenix BB25 Self-Test Project",
            "currency": "USD",
        },
        "quantities": {
            "project_id": project_id,
            "records": [
                {
                    "quantity_id": "Q-FOUND",
                    "source_object_id": "FOUND-001",
                    "work_section": "02 Foundations",
                    "quantity_type": "foundation_volume",
                    "value": 25.0,
                    "unit": "m3",
                },
                {
                    "quantity_id": "Q-WALL",
                    "source_object_id": "WALL-001",
                    "work_section": "04 Walls and partitions",
                    "quantity_type": "gross_wall_area",
                    "value": 120.0,
                    "unit": "m2",
                },
            ],
        },
        "costs": {
            "project_id": project_id,
            "currency": "USD",
            "items": [
                {"cost_item_id": "C-FOUND", "quantity_id": "Q-FOUND", "total_cost": 50000.0},
                {"cost_item_id": "C-WALL", "quantity_id": "Q-WALL", "total_cost": 36000.0},
            ],
        },
        "planning": {
            "project_id": project_id,
            "planning_passed": True,
            "baseline_scenario_id": "BASELINE",
            "scenarios": [
                {
                    "scenario_id": "BASELINE",
                    "activities": [
                        {
                            "activity_id": "A-FOUND",
                            "start_date": "2026-02-02",
                            "finish_date": "2026-02-13",
                            "quantity_ids": ["Q-FOUND"],
                        },
                        {
                            "activity_id": "A-WALL",
                            "start_date": "2026-03-02",
                            "finish_date": "2026-03-20",
                            "quantity_ids": ["Q-WALL"],
                        },
                    ],
                }
            ],
        },
        "coordination": {"project_id": project_id, "coordination_passed": True},
        "suppliers": [
            {
                "supplier_id": "SUP-A",
                "supplier_name": "Alpha Contractors",
                "contact_name": "Alice",
                "email": "alpha@example.test",
                "country": "US",
                "approved": True,
            },
            {
                "supplier_id": "SUP-B",
                "supplier_name": "Beta Builders",
                "contact_name": "Bob",
                "email": "beta@example.test",
                "country": "US",
                "approved": True,
            },
            {
                "supplier_id": "SUP-C",
                "supplier_name": "Gamma Fast Track",
                "contact_name": "Grace",
                "email": "gamma@example.test",
                "country": "US",
                "approved": True,
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    data = source_data()
    engine = ProcurementTenderingEngine()
    initial = engine.create_procurement(
        data["metadata"],
        quantity_report=data["quantities"],
        cost_report=data["costs"],
        planning_report=data["planning"],
        coordination_report=data["coordination"],
        suppliers=data["suppliers"],
    )

    bids: list[dict] = []
    profiles = [
        ("SUP-A", "Alpha Contractors", 0.94, 16),
        ("SUP-B", "Beta Builders", 1.00, 12),
        ("SUP-C", "Gamma Fast Track", 1.10, 8),
    ]
    lines_by_package: dict[str, list] = {}
    for line in initial.tender_lines:
        lines_by_package.setdefault(line.package_id, []).append(line)
    for package in initial.packages:
        for supplier_id, supplier_name, factor, delivery in profiles:
            bids.append({
                "bid_id": f"BID-{supplier_id}-{package.package_id[-6:]}",
                "package_id": package.package_id,
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "currency": "USD",
                "submitted_date": "2026-01-15",
                "validity_days": 60,
                "delivery_workdays": delivery,
                "payment_terms": "30 days",
                "line_items": [
                    {
                        "line_id": line.line_id,
                        "total_price": round(line.benchmark_total * factor, 2),
                    }
                    for line in lines_by_package[package.package_id]
                ],
            })

    report = engine.create_procurement(
        data["metadata"],
        quantity_report=data["quantities"],
        cost_report=data["costs"],
        planning_report=data["planning"],
        coordination_report=data["coordination"],
        suppliers=data["suppliers"],
        bids=bids,
    )

    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None
        output_dir = args.output_dir

    paths = ProcurementTenderingExporter().export_all(report, output_dir)
    with zipfile.ZipFile(paths["xlsx"]) as workbook:
        xlsx_names = set(workbook.namelist())
    xlsx_valid = (
        "xl/styles.xml" in xlsx_names
        and all(f"xl/worksheets/sheet{index}.xml" in xlsx_names for index in range(1, 6))
    )
    with zipfile.ZipFile(paths["docx"]) as document:
        docx_names = set(document.namelist())
    docx_valid = {
        "[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml",
    }.issubset(docx_names)
    pdf_data = paths["pdf"].read_bytes()
    pdf_valid = pdf_data.startswith(b"%PDF-1.4") and pdf_data.rstrip().endswith(b"%%EOF")
    with zipfile.ZipFile(paths["dossier"]) as dossier:
        dossier_names = set(dossier.namelist())
    dossier_valid = {
        "procurement_report.json",
        "procurement_packages.csv",
        "tender_lines.csv",
        "supplier_register.csv",
        "bid_comparison.csv",
        "award_recommendations.csv",
        "procurement_tendering_workbook.xlsx",
        "request_for_tender.docx",
        "request_for_tender.pdf",
        "checksums.sha256",
        "PACKAGE_README.txt",
    }.issubset(dossier_names)
    checksum_count = len([
        line for line in paths["checksums"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ])
    passed = (
        report.procurement_passed
        and len(report.packages) == 2
        and len(report.evaluations) == 6
        and len(report.recommendations) == 6
        and len(paths) == 11
        and all(path.is_file() for path in paths.values())
        and xlsx_valid and docx_valid and pdf_valid and dossier_valid
        and checksum_count == 9
    )
    print(json.dumps({
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB25",
        "version": "1.0.0",
        "project_id": report.project_id,
        "currency": report.currency,
        "procurement_passed": report.procurement_passed,
        "package_count": len(report.packages),
        "tender_line_count": len(report.tender_lines),
        "supplier_count": len(report.suppliers),
        "bid_count": len(report.bids),
        "evaluation_count": len(report.evaluations),
        "recommendation_count": len(report.recommendations),
        "benchmark_budget_total": report.benchmark_budget_total,
        "xlsx_structure_valid": xlsx_valid,
        "docx_structure_valid": docx_valid,
        "pdf_structure_valid": pdf_valid,
        "dossier_structure_valid": dossier_valid,
        "checksum_entry_count": checksum_count,
        "report_fingerprint_sha256": engine.fingerprint_report(report),
        "outputs": {key: str(value) for key, value in sorted(paths.items())},
    }, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
