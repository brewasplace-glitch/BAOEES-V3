import json, unittest
from pathlib import Path
from phoenix.autonomy.nl_nen_regulatory_review_bridge import assess_nl_structural_basis, build_review_candidate_action_basis
from phoenix.autonomy.professional_review_release_workflow import validate_review_return
ROOT=Path(__file__).resolve().parents[2]
class NLNENRegulatoryReviewReleaseTests(unittest.TestCase):
    def test_01_review_package_assessment_passes_without_claiming_final_release(self): self.assertEqual(assess_nl_structural_basis(ROOT,"PROFESSIONAL_REVIEW_PACKAGE").status,"PASSED_FOR_REVIEW_PACKAGE")
    def test_02_candidate_basis_has_explicit_self_weight_and_review_lock(self):
        b=build_review_candidate_action_basis(); self.assertTrue(any(a.get("kind")=="self_weight" for a in b["actions"])); self.assertFalse(b["formal_release"]); self.assertFalse(b["for_construction"]); self.assertTrue(b["professional_review_required"])
    def test_03_candidate_basis_does_not_invent_wind_or_uls(self):
        b=build_review_candidate_action_basis(); self.assertFalse(any(a.get("category")=="wind" for a in b["actions"])); self.assertFalse(any(c.get("limit_state")=="ULS" for c in b["combinations"])); self.assertIn("ULS_PARTIAL_FACTORS_AND_PROJECT_COMBINATION_MAPPING",b["explicit_unresolved_items"])
    def test_04_draft_wind_amendment_is_not_formal_code_basis(self):
        r=json.loads((ROOT/"configs/phoenix/jurisdictions/netherlands/nl_structural_norm_regulatory_registry_v1_0.json").read_text(encoding="utf-8")); d=next(s for s in r["sources"] if s["source_id"]=="PHX-NL-EC1-WIND-2026-DRAFT-A1"); self.assertEqual(d["technical_status"],"DRAFT"); self.assertFalse(d["formal_release_use"])
    def test_05_final_run_is_blocked_before_professional_review_return(self): self.assertEqual(assess_nl_structural_basis(ROOT,"REVIEWED_FINAL_RELEASE_RUN").status,"BLOCKED")
    def test_06_incomplete_review_return_fails_closed(self): self.assertEqual(validate_review_return({"reviewer_identity_or_organization":"Example"}).status,"BLOCKED")
    def test_07_complete_review_return_creates_controlled_baseline_but_not_auto_approval(self):
        p={"reviewer_identity_or_organization":"External structural engineer","review_document_reference":"REV-001","review_document_version":"1","review_date":"2026-09-02","review_comments_or_markups":["Reviewed"],"accepted_or_corrected_design_inputs":{"status":"accepted_with_comments"},"source_artifact_hashes":{"review.pdf":"abc123"}}; r=validate_review_return(p); self.assertEqual(r.status,"PASSED"); self.assertFalse(r.controlled_baseline["automatic_professional_approval"]); self.assertIn("LOCKED",r.controlled_baseline["formal_release"])
if __name__ == "__main__": unittest.main()