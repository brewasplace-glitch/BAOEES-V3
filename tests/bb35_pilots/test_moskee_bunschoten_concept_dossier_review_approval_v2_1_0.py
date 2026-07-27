from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.concept_dossier_review_approval import (
    ConceptDossierReviewApprovalEngine,
    ConceptDossierReviewApprovalExporter,
)


ROOT = Path(__file__).resolve().parents[2]


class ConceptDossierReviewApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load = lambda relative: json.loads(
            (ROOT / relative).read_text(encoding="utf-8")
        )
        cls.engine = ConceptDossierReviewApprovalEngine()
        cls.exporter = ConceptDossierReviewApprovalExporter()
        cls.report = cls.engine.evaluate(
            dossier_summary=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "integrated_concept_dossier_v2_0_2/"
                "01_integrated_concept_dossier_summary.json"
            ),
            release_gate=load(
                "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "integrated_concept_dossier_v2_0_2/"
                "14_release_gate_status.json"
            ),
            config=load(
                "configs/projects/"
                "moskee_bunschoten_"
                "concept_dossier_review_approval_v2_1_0.json"
            ),
        )

    def test_status(self):
        self.assertEqual(
            "CONCEPT_DOSSIER_REVIEWED_PROJECT_LEADER_APPROVED",
            self.report["status"],
        )

    def test_review_id(self):
        self.assertEqual(
            "HBM-CD-REV-2026-001",
            self.report["review_id"],
        )

    def test_dossier_id(self):
        self.assertEqual(
            "HBM-CD-2026-001",
            self.report["dossier_id"],
        )

    def test_twelve_review_checks(self):
        self.assertEqual(12, self.report["review_check_count"])

    def test_all_review_checks_passed(self):
        self.assertEqual(12, self.report["review_checks_passed"])
        self.assertTrue(self.report["all_review_checks_passed"])

    def test_no_open_project_leader_findings(self):
        self.assertEqual(
            0,
            self.report[
                "unresolved_project_leader_review_findings"
            ],
        )

    def test_approval_role(self):
        self.assertEqual(
            "project_leader",
            self.report["approval"]["approver_role"],
        )

    def test_approval_method(self):
        self.assertEqual(
            "EXPLICIT_PROJECT_LEADER_INSTRUCTION",
            self.report["approval"]["approval_method"],
        )

    def test_not_qualified_signature(self):
        self.assertEqual(
            (
                "INTERNAL_APPROVAL_RECORDED_"
                "NOT_QUALIFIED_ELECTRONIC_SIGNATURE"
            ),
            self.report["approval"]["signature_status"],
        )

    def test_approval_scope(self):
        self.assertEqual(
            (
                "PILOT_VALIDATION_AND_"
                "PROFESSIONAL_EVIDENCE_REPLACEMENT"
            ),
            self.report["approval"]["approval_scope"],
        )

    def test_seven_requests(self):
        self.assertEqual(7, self.report["request_count"])

    def test_drawing_count(self):
        self.assertEqual(8, self.report["drawing_register_count"])

    def test_calculation_count(self):
        self.assertEqual(
            8,
            self.report["calculation_register_count"],
        )

    def test_assumption_count(self):
        self.assertEqual(8, self.report["assumption_count"])

    def test_consistency_count(self):
        self.assertEqual(11, self.report["consistency_check_count"])

    def test_six_blockers(self):
        self.assertEqual(
            6,
            self.report["professional_blocker_count"],
        )

    def test_parking_basis(self):
        self.assertEqual(225, self.report["parking_basis_spaces"])

    def test_req107_closed(self):
        self.assertEqual(
            "CLOSED_PROJECT_LEADER_APPROVED",
            self.report["req107_status"],
        )

    def test_review_completed_gate(self):
        self.assertTrue(
            self.report["gates"][
                "concept_dossier_review_completed"
            ]
        )

    def test_approval_recorded_gate(self):
        self.assertTrue(
            self.report["gates"][
                "project_leader_approval_recorded"
            ]
        )

    def test_replacement_allowed(self):
        self.assertTrue(
            self.report["gates"][
                "professional_evidence_replacement_allowed"
            ]
        )

    def test_final_generation_blocked(self):
        self.assertFalse(
            self.report["gates"][
                "final_permit_ready_generation_allowed"
            ]
        )

    def test_bb36_functional_passed(self):
        self.assertTrue(
            self.report["gates"][
                "bb36_functional_validation_passed"
            ]
        )

    def test_bb36_production_locked(self):
        self.assertFalse(
            self.report["gates"][
                "bb36_production_release_allowed"
            ]
        )

    def test_export_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.exporter.export_all(self.report, tmp)
            count = sum(
                1 for path in Path(tmp).rglob("*")
                if path.is_file()
            )
            self.assertEqual(14, count)

    def test_canonical_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.exporter.export_all(self.report, tmp)
            with zipfile.ZipFile(paths["dossier"]) as archive:
                infos = archive.infolist()
            self.assertTrue(infos)
            self.assertTrue(all(
                info.compress_type == zipfile.ZIP_STORED
                and info.create_system == 3
                and info.date_time == (2020, 1, 1, 0, 0, 0)
                for info in infos
            ))

    def test_two_exports_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.exporter.export_all(self.report, first)
            self.exporter.export_all(self.report, second)
            first_root = Path(first)
            second_root = Path(second)
            names = sorted(
                path.relative_to(first_root).as_posix()
                for path in first_root.rglob("*")
                if path.is_file()
            )
            self.assertEqual(
                names,
                sorted(
                    path.relative_to(second_root).as_posix()
                    for path in second_root.rglob("*")
                    if path.is_file()
                ),
            )
            self.assertTrue(all(
                (first_root / name).read_bytes()
                == (second_root / name).read_bytes()
                for name in names
            ))


if __name__ == "__main__":
    unittest.main()
