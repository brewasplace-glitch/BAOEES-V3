from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.construction_documentation import (
    ConstructionDocumentationEngine,
    ConstructionDocumentationExporter,
)


def project_metadata() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "project_name": "BB23 Test Project",
        "client": "Phoenix Test Client",
        "location": "Test location",
        "jurisdiction": "TEST",
    }


def building_model() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "schema_version": "phoenix.building-model/1.0",
        "levels": [{"id": "L0"}, {"id": "L1"}],
        "elements": [
            {"id": "WALL-001", "category": "wall"},
            {"id": "DOOR-001", "category": "door"},
        ],
    }


def drawing_manifest() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "drawings": [
            {
                "drawing_id": "A-101",
                "title": "Ground floor plan",
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
    }


def structural_report() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "status": "concept",
        "structural_elements": [
            {"id": "BEAM-001"},
            {"id": "COLUMN-001"},
        ],
        "non_certifying": True,
    }


def quantity_report() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "totals_by_unit": {"ea": 4, "m2": 80.0, "m3": 12.5},
        "records": [
            {
                "quantity_id": "Q-001",
                "source_object_id": "WALL-001",
                "value": 80.0,
                "unit": "m2",
            },
            {
                "quantity_id": "Q-002",
                "source_object_id": "BEAM-001",
                "value": 12.5,
                "unit": "m3",
            },
        ],
    }


def cost_report() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "currency": "USD",
        "price_date": "2026-01-01",
        "grand_total": 125000.0,
        "items": [
            {
                "cost_item_id": "C-001",
                "quantity_id": "Q-001",
                "total_cost": 50000.0,
            },
            {
                "cost_item_id": "C-002",
                "quantity_id": "Q-002",
                "total_cost": 75000.0,
            },
        ],
    }


def clean_coordination_report() -> dict:
    return {
        "project_id": "PHX-BB23-TEST",
        "coordination_passed": True,
        "summary_by_severity": {
            "critical": 0,
            "error": 0,
            "warning": 1,
            "info": 0,
        },
        "issues": [
            {
                "issue_id": "BCI-WARNING",
                "severity": "warning",
                "status": "open",
            }
        ],
    }


def assemble_clean(
    engine: ConstructionDocumentationEngine,
    *,
    release_requested: bool = False,
):
    return engine.assemble(
        project_metadata(),
        building_model=building_model(),
        drawing_manifest=drawing_manifest(),
        structural_report=structural_report(),
        quantity_report=quantity_report(),
        cost_report=cost_report(),
        coordination_report=clean_coordination_report(),
        revision="P01",
        stage="concept",
        release_requested=release_requested,
    )


class ConstructionDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ConstructionDocumentationEngine()
        self.exporter = ConstructionDocumentationExporter()

    def test_complete_package_contains_ten_sections(self) -> None:
        package = assemble_clean(self.engine)
        self.assertEqual(10, len(package.sections))

    def test_document_register_contains_eight_outputs(self) -> None:
        package = assemble_clean(self.engine)
        self.assertEqual(8, len(package.document_register))

    def test_release_request_releases_clean_package(self) -> None:
        package = assemble_clean(self.engine, release_requested=True)
        self.assertEqual("released", package.status.value)
        self.assertTrue(package.release_ready)
        self.assertTrue(
            all(
                record.status.value == "released"
                for record in package.document_register
            )
        )

    def test_open_coordination_error_blocks_release(self) -> None:
        coordination = clean_coordination_report()
        coordination["coordination_passed"] = False
        coordination["issues"].append(
            {
                "issue_id": "BCI-ERROR",
                "severity": "error",
                "status": "open",
            }
        )
        package = self.engine.assemble(
            project_metadata(),
            building_model=building_model(),
            drawing_manifest=drawing_manifest(),
            structural_report=structural_report(),
            quantity_report=quantity_report(),
            cost_report=cost_report(),
            coordination_report=coordination,
            release_requested=True,
        )
        self.assertEqual("blocked", package.status.value)
        self.assertGreater(package.blocking_issue_count, 0)

    def test_missing_required_source_blocks_package(self) -> None:
        package = self.engine.assemble(
            project_metadata(),
            building_model=building_model(),
            drawing_manifest=drawing_manifest(),
            structural_report=structural_report(),
            quantity_report=quantity_report(),
            cost_report=cost_report(),
            coordination_report=None,
        )
        self.assertEqual("blocked", package.status.value)
        self.assertTrue(
            any(
                issue.source == "coordination_report"
                for issue in package.issues
            )
        )

    def test_project_identity_conflict_is_critical(self) -> None:
        quantities = quantity_report()
        quantities["project_id"] = "OTHER-PROJECT"
        package = self.engine.assemble(
            project_metadata(),
            building_model=building_model(),
            drawing_manifest=drawing_manifest(),
            structural_report=structural_report(),
            quantity_report=quantities,
            cost_report=cost_report(),
            coordination_report=clean_coordination_report(),
        )
        self.assertTrue(
            any(
                issue.code == "DOC-PROJECT-001"
                and issue.severity == "critical"
                for issue in package.issues
            )
        )

    def test_revision_format_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.assemble(project_metadata(), revision="REV-1")

    def test_mapping_adapter_with_to_dict_is_supported(self) -> None:
        class MetadataObject:
            def to_dict(self) -> dict:
                return project_metadata()

        package = self.engine.assemble(
            MetadataObject(),
            building_model=building_model(),
            drawing_manifest=drawing_manifest(),
            structural_report=structural_report(),
            quantity_report=quantity_report(),
            cost_report=cost_report(),
            coordination_report=clean_coordination_report(),
        )
        self.assertEqual("PHX-BB23-TEST", package.project_id)

    def test_drawing_register_is_in_report_sections(self) -> None:
        package = assemble_clean(self.engine)
        drawing_section = next(
            section
            for section in package.sections
            if section.section_id == "SEC-04"
        )
        self.assertEqual(2, len(drawing_section.entries))

    def test_quantity_summary_retains_unit_totals(self) -> None:
        package = assemble_clean(self.engine)
        section = next(
            item
            for item in package.sections
            if item.section_id == "SEC-06"
        )
        totals = {entry["unit"]: entry["value"] for entry in section.entries}
        self.assertEqual(80.0, totals["m2"])

    def test_cost_summary_retains_total_and_currency(self) -> None:
        package = assemble_clean(self.engine)
        section = next(
            item
            for item in package.sections
            if item.section_id == "SEC-07"
        )
        self.assertEqual("USD", section.entries[0]["currency"])
        self.assertEqual(125000.0, section.entries[0]["total_cost"])

    def test_package_fingerprint_is_deterministic(self) -> None:
        first = assemble_clean(self.engine)
        second = assemble_clean(self.engine)
        self.assertEqual(
            self.engine.fingerprint_package(first),
            self.engine.fingerprint_package(second),
        )

    def test_export_all_creates_every_output(self) -> None:
        package = assemble_clean(self.engine, release_requested=True)
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(package, tmp)
            self.assertEqual(
                {
                    "manifest",
                    "register",
                    "markdown",
                    "html",
                    "docx",
                    "pdf",
                    "checksums",
                    "dossier",
                },
                set(paths),
            )
            self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_manifest_and_register_match_package(self) -> None:
        package = assemble_clean(self.engine)
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(package, tmp)
            manifest = json.loads(
                paths["manifest"].read_text(encoding="utf-8")
            )
            self.assertEqual(package.package_id, manifest["package_id"])
            with paths["register"].open(
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(package.document_register), len(rows))

    def test_docx_package_contains_required_ooxml_parts(self) -> None:
        package = assemble_clean(self.engine)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.exporter.export_docx(package, Path(tmp) / "report.docx")
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
            self.assertTrue(
                {
                    "[Content_Types].xml",
                    "_rels/.rels",
                    "word/document.xml",
                    "word/styles.xml",
                }.issubset(names)
            )

    def test_pdf_has_valid_header_and_eof_marker(self) -> None:
        package = assemble_clean(self.engine)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.exporter.export_pdf(package, Path(tmp) / "report.pdf")
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-1.4"))
            self.assertTrue(data.rstrip().endswith(b"%%EOF"))

    def test_dossier_contains_publication_files(self) -> None:
        package = assemble_clean(self.engine)
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(package, tmp)
            with zipfile.ZipFile(paths["dossier"]) as archive:
                names = set(archive.namelist())
            self.assertIn("technical_project_report.pdf", names)
            self.assertIn("technical_project_report.docx", names)
            self.assertIn("checksums.sha256", names)
            self.assertIn("PACKAGE_README.txt", names)


if __name__ == "__main__":
    unittest.main()
