"""BB23 self-test runner."""

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

from phoenix.construction_documentation import (
    ConstructionDocumentationEngine,
    ConstructionDocumentationExporter,
)


def sample_inputs() -> dict:
    project_id = "PHX-BB23-SELFTEST"
    return {
        "project_metadata": {
            "project_id": project_id,
            "project_name": "Phoenix BB23 Self-Test Project",
            "client": "PROJECT-PHOENIX",
            "location": "Validation environment",
            "jurisdiction": "TEST",
            "author": "Phoenix Construction Documentation Engine",
        },
        "building_model": {
            "project_id": project_id,
            "schema_version": "phoenix.building-model/1.0",
            "levels": [{"id": "L0"}, {"id": "L1"}],
            "elements": [
                {"id": "WALL-001", "category": "wall"},
                {"id": "DOOR-001", "category": "door"},
                {"id": "SLAB-001", "category": "slab"},
            ],
        },
        "drawing_manifest": {
            "project_id": project_id,
            "drawings": [
                {
                    "drawing_id": "A-101",
                    "title": "Ground floor plan",
                    "revision": "P01",
                    "status": "for_review",
                },
                {
                    "drawing_id": "A-201",
                    "title": "Elevations",
                    "revision": "P01",
                    "status": "for_review",
                },
                {
                    "drawing_id": "S-101",
                    "title": "Structural plan",
                    "revision": "P01",
                    "status": "for_review",
                },
            ],
        },
        "structural_report": {
            "project_id": project_id,
            "status": "concept",
            "non_certifying": True,
            "structural_elements": [
                {"id": "BEAM-001"},
                {"id": "COLUMN-001"},
                {"id": "FOUNDATION-001"},
            ],
        },
        "quantity_report": {
            "project_id": project_id,
            "records": [
                {
                    "quantity_id": "Q-001",
                    "source_object_id": "WALL-001",
                    "value": 90.0,
                    "unit": "m2",
                },
                {
                    "quantity_id": "Q-002",
                    "source_object_id": "SLAB-001",
                    "value": 18.0,
                    "unit": "m3",
                },
            ],
            "totals_by_unit": {
                "ea": 6,
                "m2": 90.0,
                "m3": 18.0,
            },
        },
        "cost_report": {
            "project_id": project_id,
            "currency": "USD",
            "price_date": "2026-01-01",
            "grand_total": 245000.0,
            "items": [
                {
                    "cost_item_id": "C-001",
                    "quantity_id": "Q-001",
                    "total_cost": 95000.0,
                },
                {
                    "cost_item_id": "C-002",
                    "quantity_id": "Q-002",
                    "total_cost": 150000.0,
                },
            ],
        },
        "coordination_report": {
            "project_id": project_id,
            "coordination_passed": True,
            "summary_by_severity": {
                "critical": 0,
                "error": 0,
                "warning": 1,
                "info": 1,
            },
            "issues": [
                {
                    "issue_id": "BCI-INFO",
                    "severity": "info",
                    "status": "open",
                },
                {
                    "issue_id": "BCI-WARNING",
                    "severity": "warning",
                    "status": "open",
                },
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    data = sample_inputs()
    engine = ConstructionDocumentationEngine()
    exporter = ConstructionDocumentationExporter()
    package = engine.assemble(
        data["project_metadata"],
        building_model=data["building_model"],
        drawing_manifest=data["drawing_manifest"],
        structural_report=data["structural_report"],
        quantity_report=data["quantity_report"],
        cost_report=data["cost_report"],
        coordination_report=data["coordination_report"],
        revision="P01",
        stage="concept",
        release_requested=True,
    )

    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        temporary = None
        output_dir = args.output_dir

    paths = exporter.export_all(package, output_dir)

    with zipfile.ZipFile(paths["docx"]) as archive:
        docx_valid = {
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
            "word/styles.xml",
        }.issubset(set(archive.namelist()))

    pdf_data = paths["pdf"].read_bytes()
    pdf_valid = (
        pdf_data.startswith(b"%PDF-1.4")
        and pdf_data.rstrip().endswith(b"%%EOF")
    )

    with zipfile.ZipFile(paths["dossier"]) as archive:
        dossier_names = set(archive.namelist())
    dossier_valid = {
        "construction_documentation_manifest.json",
        "document_register.csv",
        "technical_project_report.docx",
        "technical_project_report.pdf",
        "checksums.sha256",
        "PACKAGE_README.txt",
    }.issubset(dossier_names)

    checksum_lines = [
        line
        for line in paths["checksums"].read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    passed = (
        package.status.value == "released"
        and package.release_ready
        and len(package.sections) == 10
        and len(package.document_register) == 8
        and len(paths) == 8
        and all(path.is_file() for path in paths.values())
        and docx_valid
        and pdf_valid
        and dossier_valid
        and len(checksum_lines) == 6
    )

    result = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB23",
        "version": "1.0.0",
        "project_id": package.project_id,
        "package_id": package.package_id,
        "package_status": package.status.value,
        "release_ready": package.release_ready,
        "section_count": len(package.sections),
        "document_count": len(package.document_register),
        "blocking_issue_count": package.blocking_issue_count,
        "package_fingerprint_sha256": engine.fingerprint_package(package),
        "docx_structure_valid": docx_valid,
        "pdf_structure_valid": pdf_valid,
        "dossier_structure_valid": dossier_valid,
        "checksum_entry_count": len(checksum_lines),
        "outputs": {
            key: str(path)
            for key, path in sorted(paths.items())
        },
    }
    print(json.dumps(result, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
