from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.professional_evidence_replacement_programme import (
    ProfessionalEvidenceReplacementProgrammeEngine,
    ProfessionalEvidenceReplacementProgrammeExporter,
)

ROOT = Path(__file__).resolve().parents[2]


class ProfessionalEvidenceReplacementProgrammeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda relative: json.loads((ROOT / relative).read_text(encoding="utf-8"))
        cls.config = load(
            "configs/projects/"
            "moskee_bunschoten_professional_evidence_replacement_programme_v2_2_0.json"
        )
        cls.report = ProfessionalEvidenceReplacementProgrammeEngine().evaluate(
            review_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "concept_dossier_review_project_leader_approval_v2_1_0/"
                "01_review_approval_summary.json"
            ),
            orchestrator_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "unified_model_driven_production_orchestrator_v1_0_0/"
                "01_orchestrator_summary.json"
            ),
            release_gate=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "unified_model_driven_production_orchestrator_v1_0_0/"
                "14_release_gate_status.json"
            ),
            config=cls.config,
        )
        cls.exporter = ProfessionalEvidenceReplacementProgrammeExporter()

    def test_status(self):
        self.assertEqual("PROFESSIONAL_EVIDENCE_REPLACEMENT_PROGRAMME_READY", self.report["status"])

    def test_programme_id(self):
        self.assertEqual("HBM-PERP-2026-001", self.report["programme_id"])

    def test_six_requests(self):
        self.assertEqual(6, self.report["replacement_request_count"])

    def test_exact_request_ids(self):
        self.assertEqual(
            ["REQ-102", "REQ-103", "REQ-104", "REQ-105", "REQ-106", "REQ-108"],
            self.report["replacement_requests"],
        )

    def test_req107_excluded(self):
        self.assertEqual("REQ-107", self.report["excluded_closed_request"])

    def test_req107_closed(self):
        self.assertEqual("CLOSED_PROJECT_LEADER_APPROVED", self.report["req107_status"])

    def test_parking_basis(self):
        self.assertEqual(225, self.report["parking_basis_spaces"])

    def test_workpacks_ready(self):
        self.assertTrue(all(item["workpack_status"] == "READY_FOR_ISSUE" for item in self.report["workpacks"]))

    def test_all_evidence_pending(self):
        self.assertTrue(all(item["evidence_status"] == "PENDING" for item in self.report["workpacks"]))

    def test_twelve_gate_checks(self):
        self.assertEqual(12, self.report["gate_check_count"])

    def test_all_gate_checks_pass(self):
        self.assertEqual(12, self.report["gate_checks_passed"])
        self.assertTrue(self.report["all_gate_checks_passed"])

    def test_programme_ready_gate(self):
        self.assertTrue(self.report["gates"]["programme_ready"])

    def test_adviser_issue_allowed(self):
        self.assertTrue(self.report["gates"]["adviser_issue_allowed"])

    def test_intake_allowed(self):
        self.assertTrue(self.report["gates"]["evidence_intake_allowed"])

    def test_validation_not_complete(self):
        self.assertFalse(self.report["gates"]["evidence_validation_complete"])

    def test_no_evidence_accepted(self):
        self.assertEqual(0, self.report["professional_evidence_accepted_count"])

    def test_six_blockers_remain(self):
        self.assertEqual(6, self.report["professional_evidence_blocker_count"])

    def test_final_generation_blocked(self):
        self.assertFalse(self.report["gates"]["final_permit_ready_generation_allowed"])

    def test_bb36_locked(self):
        self.assertFalse(self.report["gates"]["bb36_production_release_allowed"])

    def test_each_request_has_inputs(self):
        self.assertTrue(all(item["required_inputs"] for item in self.config["requests"]))

    def test_each_request_has_criteria(self):
        self.assertTrue(all(item["criteria"] for item in self.config["requests"]))

    def test_req105_has_eight_inputs(self):
        item = next(value for value in self.config["requests"] if value["request_id"] == "REQ-105")
        self.assertEqual(8, len(item["required_inputs"]))

    def test_req106_parking_lead(self):
        item = next(value for value in self.config["requests"] if value["request_id"] == "REQ-106")
        self.assertEqual("traffic_or_parking_adviser", item["lead_role"])

    def test_req108_aerius_lead(self):
        item = next(value for value in self.config["requests"] if value["request_id"] == "REQ-108")
        self.assertEqual("aerius_or_nitrogen_adviser", item["lead_role"])

    def test_export_file_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, self.config, tmp)
            self.assertEqual(60, sum(1 for path in Path(tmp).rglob("*") if path.is_file()))

    def test_six_individual_workpack_zips(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, self.config, tmp)
            zips = list(Path(tmp).glob("BB35_PILOT_1_REQ-*_PROFESSIONAL_EVIDENCE_WORKPACK_v2_2_0.zip"))
            self.assertEqual(6, len(zips))

    def test_individual_zips_are_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, self.config, tmp)
            with zipfile.ZipFile(paths["req_102_package"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED and info.date_time == (2020, 1, 1, 0, 0, 0) for info in infos))

    def test_programme_zip_is_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, self.config, tmp)
            with zipfile.ZipFile(paths["programme_package"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED and info.date_time == (2020, 1, 1, 0, 0, 0) for info in infos))

    def test_two_exports_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.exporter.export_all(self.report, self.config, first)
            self.exporter.export_all(self.report, self.config, second)
            first_root = Path(first)
            second_root = Path(second)
            names = sorted(path.relative_to(first_root).as_posix() for path in first_root.rglob("*") if path.is_file())
            self.assertEqual(names, sorted(path.relative_to(second_root).as_posix() for path in second_root.rglob("*") if path.is_file()))
            self.assertTrue(all((first_root / name).read_bytes() == (second_root / name).read_bytes() for name in names))

    def test_fingerprint_present(self):
        self.assertEqual(64, len(self.report["programme_fingerprint_sha256"]))


if __name__ == "__main__":
    unittest.main()
