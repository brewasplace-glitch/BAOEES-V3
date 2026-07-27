from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.uploaded_evidence_intake import (
    UploadedEvidenceIntakeEngine,
    UploadedEvidenceIntakeExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class UploadedEvidenceIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(
            (
                ROOT / "inputs/pilots/moskee_bunschoten/"
                "uploaded_evidence_manifest_v1_4_1.json"
            ).read_text(encoding="utf-8")
        )
        self.register = json.loads(
            (
                ROOT / "inputs/pilots/moskee_bunschoten/"
                "verified_inputs_register_v1_2_0.json"
            ).read_text(encoding="utf-8")
        )
        self.root = (
            ROOT / "inputs/pilots/moskee_bunschoten/"
            "uploaded_evidence/v1_4_1"
        )
        self.engine = UploadedEvidenceIntakeEngine()
        self.exporter = UploadedEvidenceIntakeExporter()

    def evaluate(self):
        return self.engine.evaluate(
            manifest=self.manifest,
            register=self.register,
            evidence_root=self.root,
        )

    def test_all_six_files_are_valid(self):
        report = self.evaluate()
        self.assertEqual(6, report["received_file_count"])
        self.assertEqual(6, report["valid_file_count"])

    def test_existing_drawing_request_is_closed(self):
        request = next(
            item for item in self.evaluate()["request_statuses"]
            if item["request_id"] == "REQ-101"
        )
        self.assertEqual("CLOSED_VERIFIED", request["status"])
        self.assertFalse(request["blocking"])

    def test_cadastral_request_is_partial(self):
        request = next(
            item for item in self.evaluate()["request_statuses"]
            if item["request_id"] == "REQ-102"
        )
        self.assertEqual(
            "RECEIVED_PENDING_GEOMETRY_VALIDATION",
            request["status"],
        )
        self.assertTrue(request["blocking"])

    def test_structural_request_is_partial(self):
        request = next(
            item for item in self.evaluate()["request_statuses"]
            if item["request_id"] == "REQ-103"
        )
        self.assertIn("CURRENT_SURVEY_PENDING", request["status"])
        self.assertTrue(request["blocking"])

    def test_dwg_is_ac1032(self):
        dwg = next(
            item for item in self.manifest["files"]
            if item["file_type"] == "dwg"
        )
        self.assertEqual("AC1032", dwg["dwg_signature"])
        self.assertEqual("AutoCAD 2018/2019/2020", dwg["detected_version"])

    def test_existing_pdf_has_19_pages(self):
        item = next(
            item for item in self.manifest["files"]
            if item["evidence_id"] == "HBM-ING-001"
        )
        self.assertEqual(19, item["page_count"])

    def test_structural_pdf_has_10_pages(self):
        item = next(
            item for item in self.manifest["files"]
            if item["evidence_id"] == "HBM-ING-003"
        )
        self.assertEqual(10, item["page_count"])

    def test_three_png_files_are_registered(self):
        items = [
            item for item in self.manifest["files"]
            if item["file_type"] == "png"
        ]
        self.assertEqual(3, len(items))
        self.assertTrue(all(item["width_px"] > 1600 for item in items))

    def test_request_summary_is_one_two_five(self):
        report = self.evaluate()
        self.assertEqual(1, report["closed_request_count"])
        self.assertEqual(2, report["partial_request_count"])
        self.assertEqual(5, report["open_request_count"])

    def test_remaining_blocking_inputs_is_seven(self):
        self.assertEqual(
            7,
            self.evaluate()["remaining_blocking_input_count"],
        )

    def test_verified_project_facts_increase_to_ten(self):
        self.assertEqual(
            10,
            self.evaluate()["verified_project_fact_count"],
        )

    def test_final_generation_remains_blocked(self):
        report = self.evaluate()
        self.assertFalse(report["final_generation_allowed"])
        self.assertFalse(report["bb36_unlock_allowed"])

    def test_modified_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for source in self.root.iterdir():
                (target / source.name).write_bytes(source.read_bytes())
            first = next(target.iterdir())
            first.write_bytes(b"modified")
            report = self.engine.evaluate(
                manifest=self.manifest,
                register=self.register,
                evidence_root=target,
            )
            self.assertEqual("INVALID_UPLOADED_EVIDENCE", report["status"])

    def test_exports_are_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.evaluate(), tmp)
            self.assertEqual(6, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_dossier_uses_canonical_stored_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.evaluate(), tmp)
            with zipfile.ZipFile(paths["dossier"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(
                info.compress_type == zipfile.ZIP_STORED
                and info.create_system == 3
                for info in infos
            ))


if __name__ == "__main__":
    unittest.main()
