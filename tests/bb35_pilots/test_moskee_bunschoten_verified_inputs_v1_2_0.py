from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.verified_inputs import (
    MoskeeBunschotenVerifiedInputsGate,
)
from phoenix.bb35_pilots.moskee_bunschoten.verified_inputs_exporters import (
    MoskeeBunschotenVerifiedInputsExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class VerifiedInputsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            (
                ROOT
                / "configs/projects/"
                "moskee_bunschoten_bb35_pilot_1.json"
            ).read_text(encoding="utf-8")
        )
        self.register = json.loads(
            (
                ROOT
                / "inputs/pilots/moskee_bunschoten/"
                "verified_inputs_register_v1_2_0.json"
            ).read_text(encoding="utf-8")
        )
        self.baseline_manifest = json.loads(
            (
                ROOT
                / "inputs/pilots/moskee_bunschoten/"
                "evidence_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.admin_manifest = json.loads(
            (
                ROOT
                / "inputs/pilots/moskee_bunschoten/"
                "administrative_evidence_manifest_v1_2_0.json"
            ).read_text(encoding="utf-8")
        )
        self.engine = MoskeeBunschotenVerifiedInputsGate()
        self.exporter = MoskeeBunschotenVerifiedInputsExporter()

    def evaluate(self):
        return self.engine.evaluate(
            config=self.config,
            register=self.register,
            baseline_manifest=self.baseline_manifest,
            baseline_evidence_root=(
                ROOT
                / "inputs/pilots/moskee_bunschoten/"
                "source_evidence"
            ),
            administrative_manifest=self.admin_manifest,
            administrative_evidence_root=(
                ROOT
                / "inputs/pilots/moskee_bunschoten/"
                "verified_inputs/administrative_evidence"
            ),
        )

    def test_all_thirteen_evidence_files_validate(self) -> None:
        report = self.evaluate()
        self.assertEqual(13, report["evidence_count"])
        self.assertEqual(13, report["valid_evidence_count"])

    def test_scope_b_remains_authoritative(self) -> None:
        scope = self.evaluate()["authoritative_scope"]
        self.assertEqual("B", scope["selected_option"])
        self.assertEqual(140.0, scope["gross_extension_area_m2"])

    def test_six_verified_project_facts_exist(self) -> None:
        self.assertEqual(6, self.evaluate()["verified_fact_count"])

    def test_eight_external_inputs_are_pending(self) -> None:
        self.assertEqual(8, self.evaluate()["pending_input_count"])

    def test_status_is_blocked_pending_external_evidence(self) -> None:
        self.assertEqual(
            "BLOCKED_PENDING_EXTERNAL_TECHNICAL_EVIDENCE",
            self.evaluate()["status"],
        )

    def test_concept_generation_is_allowed(self) -> None:
        self.assertTrue(
            self.evaluate()["concept_generation_allowed"]
        )

    def test_final_generation_is_blocked(self) -> None:
        self.assertFalse(
            self.evaluate()["final_generation_allowed"]
        )

    def test_structural_design_is_not_concept_ready(self) -> None:
        structural = next(
            item
            for item in self.evaluate()["downstream_readiness"]
            if item["module"] == "structural_design"
        )
        self.assertFalse(structural["concept_allowed"])
        self.assertFalse(structural["final_ready"])

    def test_building_model_concept_is_allowed(self) -> None:
        model = next(
            item
            for item in self.evaluate()["downstream_readiness"]
            if item["module"] == "building_model"
        )
        self.assertTrue(model["concept_allowed"])
        self.assertFalse(model["final_ready"])

    def test_original_drawing_is_still_pending(self) -> None:
        pending = {
            item["input_id"]: item
            for item in self.evaluate()["pending_inputs"]
        }
        self.assertIn("HBM-VI-101", pending)

    def test_cadastral_dwg_is_still_pending(self) -> None:
        pending = {
            item["input_id"]: item
            for item in self.evaluate()["pending_inputs"]
        }
        self.assertIn("HBM-VI-102", pending)

    def test_parking_field_measurement_is_pending(self) -> None:
        pending = {
            item["input_id"]: item
            for item in self.evaluate()["pending_inputs"]
        }
        self.assertIn("HBM-VI-106", pending)

    def test_aerius_activity_data_is_pending(self) -> None:
        pending = {
            item["input_id"]: item
            for item in self.evaluate()["pending_inputs"]
        }
        self.assertIn("HBM-VI-108", pending)

    def test_bb36_remains_locked(self) -> None:
        self.assertFalse(self.evaluate()["bb36_unlock_allowed"])

    def test_exports_create_complete_dossier(self) -> None:
        report = self.evaluate()
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(report, tmp)
            self.assertEqual(9, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))
            with zipfile.ZipFile(paths["dossier"]) as archive:
                names = set(archive.namelist())
            self.assertIn("verified_inputs_gate_report.json", names)
            self.assertIn("pending_external_inputs.csv", names)
            self.assertIn("VERIFIED_INPUTS_README.txt", names)


if __name__ == "__main__":
    unittest.main()
