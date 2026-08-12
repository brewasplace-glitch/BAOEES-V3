from __future__ import annotations

import unittest

from phoenix.autonomy.package_d_weak_storey_screening_review_r9_5_2_7 import (
    PACKAGE_ID,
    REVIEW_ACCEPTED,
    REVIEW_NOT_ACCEPTED,
    discover_package_d_input,
    required_template,
    run_package_d_weak_storey_screening_review_r9_5_2_7,
    validate_package_d_input,
)


class PackageDWeakStoreyScreeningReviewR9527Tests(unittest.TestCase):
    def test_required_template_does_not_fabricate_review(self):
        value = required_template()
        self.assertEqual(value["package_id"], PACKAGE_ID)
        self.assertEqual(value["review_status"], "INPUT_REQUIRED")
        self.assertIsNone(value["screening_proxy_accepted_for_candidate_gate"])
        self.assertIsNone(value["screening_proxy_review_reference"])
        self.assertIsNone(value["reviewer_scope"])

    def test_missing_input_remains_input_required_and_locked(self):
        result = validate_package_d_input(None)
        self.assertEqual(result["status"], "INPUT_REQUIRED")
        self.assertFalse(result["eligible_for_r9_5_promotion"])
        self.assertFalse(result["safety"]["automatic_screening_proxy_acceptance"])
        self.assertFalse(result["safety"]["automatic_professional_approval"])
        self.assertEqual(result["safety"]["production_release"], "LOCKED")
        self.assertEqual(result["safety"]["for_construction_release"], "LOCKED")

    def test_complete_accepted_review_is_only_eligible_for_later_promotion(self):
        value = required_template()
        value.update({
            "screening_proxy_accepted_for_candidate_gate": True,
            "screening_proxy_review_reference": "PRO-REVIEW-WEAK-001",
            "reviewer_scope": "Professional structural review of candidate weak-storey screening proxy",
            "review_status": REVIEW_ACCEPTED,
        })
        result = validate_package_d_input(value)
        self.assertTrue(result["review_complete"])
        self.assertTrue(result["screening_proxy_accepted_for_candidate_gate"])
        self.assertTrue(result["eligible_for_r9_5_promotion"])
        self.assertEqual(result["status"], "ELIGIBLE_FOR_LATER_R9_5_PROMOTION")
        self.assertFalse(result["safety"]["automatic_r9_5_promotion"])
        self.assertFalse(result["safety"]["automatic_code_compliance_claim"])

    def test_complete_rejected_review_does_not_become_eligible(self):
        value = required_template()
        value.update({
            "screening_proxy_accepted_for_candidate_gate": False,
            "screening_proxy_review_reference": "PRO-REVIEW-WEAK-002",
            "reviewer_scope": "Professional structural review of candidate weak-storey screening proxy",
            "review_status": REVIEW_NOT_ACCEPTED,
        })
        result = validate_package_d_input(value)
        self.assertTrue(result["review_complete"])
        self.assertFalse(result["eligible_for_r9_5_promotion"])
        self.assertEqual(result["status"], "REVIEWED_NOT_ACCEPTED_FOR_CANDIDATE_GATE")

    def test_inconsistent_status_and_boolean_is_invalid(self):
        value = required_template()
        value.update({
            "screening_proxy_accepted_for_candidate_gate": False,
            "screening_proxy_review_reference": "PRO-REVIEW-WEAK-003",
            "reviewer_scope": "Professional structural review",
            "review_status": REVIEW_ACCEPTED,
        })
        result = validate_package_d_input(value)
        self.assertFalse(result["eligible_for_r9_5_promotion"])
        self.assertIn(
            "review_status_vs_screening_proxy_accepted_for_candidate_gate",
            result["invalid_requirements"],
        )

    def test_discovery_finds_package_d_in_package_inputs(self):
        source = {
            "evidence_intake": {
                "package_inputs": {
                    PACKAGE_ID: {
                        "package_id": PACKAGE_ID,
                        "review_status": "INPUT_REQUIRED",
                    }
                }
            }
        }
        result = discover_package_d_input(source)
        self.assertEqual(result["package_id"], PACKAGE_ID)

    def test_chain_entry_accepts_permissive_context(self):
        result = run_package_d_weak_storey_screening_review_r9_5_2_7(
            {"unrelated": True},
            repository="C:/does-not-need-to-exist",
        )
        self.assertEqual(result["package_id"], PACKAGE_ID)
        self.assertEqual(result["status"], "INPUT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
