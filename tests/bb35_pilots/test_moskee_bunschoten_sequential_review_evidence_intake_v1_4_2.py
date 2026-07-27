from __future__ import annotations

import unittest
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.sequential_review_evidence_intake import (
    SequentialReviewEvidenceIntakeValidator,
)


ROOT = Path(__file__).resolve().parents[2]


class SequentialReviewEvidenceIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = SequentialReviewEvidenceIntakeValidator().validate(
            ROOT
        )

    def test_integrated_status(self) -> None:
        self.assertEqual(
            "REVIEW_COMPLETE_EVIDENCE_INTAKE_PARTIALLY_SATISFIED",
            self.result["status"],
        )

    def test_scope_is_authoritative_140m2(self) -> None:
        self.assertEqual(
            {
                "width_m": 7.0,
                "depth_m": 10.0,
                "storeys": 2,
                "gross_extension_area_m2": 140.0,
            },
            self.result["authoritative_scope"],
        )

    def test_review_is_complete(self) -> None:
        self.assertEqual(
            "CONCEPT_REVIEW_COMPLETE_EVIDENCE_ACQUISITION_OPEN",
            self.result["review_status"],
        )

    def test_intake_is_partial(self) -> None:
        self.assertEqual(
            "EVIDENCE_ACQUISITION_PARTIALLY_SATISFIED",
            self.result["intake_status"],
        )

    def test_six_files_are_valid(self) -> None:
        self.assertEqual(
            6,
            self.result["valid_uploaded_evidence_count"],
        )

    def test_request_counts(self) -> None:
        self.assertEqual(
            {"closed": 1, "partial": 2, "open": 5},
            self.result["evidence_requests"],
        )

    def test_seven_blockers_remain(self) -> None:
        self.assertEqual(
            7,
            self.result["remaining_blocking_input_count"],
        )

    def test_final_and_bb36_remain_locked(self) -> None:
        self.assertFalse(
            self.result["final_generation_allowed"]
        )
        self.assertFalse(self.result["bb36_unlock_allowed"])


if __name__ == "__main__":
    unittest.main()
