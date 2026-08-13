from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.professional_dossier_controlled_review_v1_0 import (
    INPUT_REQUIRED,
    READY,
    RETURN_AWAITED,
    RETURN_INVALID,
    RETURN_RECORDED,
    create_dossier,
    process_review_return,
)


def source_files(root: Path, verification_status="TECHNICALLY_CROSS_VERIFIED"):
    scia = root / "scia.json"
    scia.write_text(json.dumps({
        "status": "CALCULATED_UNVERIFIED",
        "safety": {
            "automatic_professional_approval": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }), encoding="utf-8")

    verification = root / "verification.json"
    verification.write_text(json.dumps({
        "status": verification_status,
        "safety": {
            "automatic_professional_approval": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }), encoding="utf-8")

    esa = root / "model.esa"
    esa.write_bytes(b"SCIA MODEL")
    pdf = root / "calc.pdf"
    pdf.write_bytes(b"%PDF synthetic")
    docx = root / "calc.docx"
    docx.write_bytes(b"DOCX synthetic")
    return scia, verification, esa, pdf, docx


def plan(root: Path, verification_status="TECHNICALLY_CROSS_VERIFIED"):
    scia, verification, esa, pdf, docx = source_files(root, verification_status)
    return {
        "schema_version": "phoenix.professional-dossier-plan/1.0",
        "project_id": "TEST",
        "dossier_reference": "TEST-STRUCT-REVIEW-001",
        "scia_run_result": scia.relative_to(root).as_posix(),
        "verification_result": verification.relative_to(root).as_posix(),
        "dossier_root": "dossier",
        "deliverables": [
            {"role": "SCIA_ESA", "path": esa.relative_to(root).as_posix(), "required": True},
            {"role": "STRUCTURAL_CALCULATION_PDF", "path": pdf.relative_to(root).as_posix(), "required": True},
            {"role": "EDITABLE_REPORT_DOCX", "path": docx.relative_to(root).as_posix(), "required": True},
        ],
    }


class DossierTests(unittest.TestCase):
    def repo(self):
        tmp = tempfile.TemporaryDirectory()
        return tmp, Path(tmp.name)

    def test_01_cross_verified_source_creates_ready_dossier(self):
        tmp, root = self.repo()
        try:
            result = create_dossier(plan(root), root)
            self.assertEqual(READY, result["status"])
            self.assertEqual("TECHNICALLY_CROSS_VERIFIED", result["technical_verification_status"])
            self.assertTrue((root / "dossier/PROFESSIONAL_REVIEW_HANDOFF.zip").is_file())
        finally:
            tmp.cleanup()

    def test_02_technically_verified_source_is_also_eligible_for_review(self):
        tmp, root = self.repo()
        try:
            result = create_dossier(plan(root, "TECHNICALLY_VERIFIED"), root)
            self.assertEqual(READY, result["status"])
        finally:
            tmp.cleanup()

    def test_03_unverified_source_is_blocked(self):
        tmp, root = self.repo()
        try:
            result = create_dossier(plan(root, "VERIFICATION_INPUT_REQUIRED"), root)
            self.assertEqual(INPUT_REQUIRED, result["status"])
        finally:
            tmp.cleanup()

    def test_04_required_missing_deliverable_is_blocked(self):
        tmp, root = self.repo()
        try:
            p = plan(root)
            p["deliverables"][0]["path"] = "missing.esa"
            result = create_dossier(p, root)
            self.assertEqual(INPUT_REQUIRED, result["status"])
        finally:
            tmp.cleanup()

    def test_05_manifest_contains_exact_hashes(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            manifest = json.loads((root/"dossier/DOSSIER_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(3, len(manifest["deliverables"]))
            self.assertTrue(all(len(x["sha256"]) == 64 for x in manifest["deliverables"]))
        finally:
            tmp.cleanup()

    def test_06_return_template_is_never_auto_confirmed(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            review = json.loads((root/"dossier/REVIEWER_RETURN_REQUIRED.json").read_text(encoding="utf-8"))
            self.assertFalse(review["submission_confirmed"])
            self.assertEqual("INPUT_REQUIRED", review["decision"])
        finally:
            tmp.cleanup()

    def test_07_unconfirmed_return_is_awaited(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            result = process_review_return(root, root/"dossier", root/"dossier/REVIEWER_RETURN_REQUIRED.json")
            self.assertEqual(RETURN_AWAITED, result["status"])
        finally:
            tmp.cleanup()

    def complete_review(self, root: Path, decision="REVIEWED_WITHOUT_CHANGES"):
        path = root/"dossier/REVIEWER_RETURN_REQUIRED.json"
        review = json.loads(path.read_text(encoding="utf-8"))
        review["submission_confirmed"] = True
        review["review_record"] = {
            "reviewer_name": "Reviewer",
            "reviewer_organization": "Engineering BV",
            "reviewer_role": "Structural Engineer",
            "review_date": "2026-08-13",
            "signature_reference": "SIG-001",
            "professional_scope": "Structural calculation and SCIA model review",
        }
        review["decision"] = decision
        review["review_comment"] = "Synthetic test review."
        path.write_text(json.dumps(review), encoding="utf-8")
        return path, review

    def test_08_missing_reviewer_identity_is_invalid(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            path = root/"dossier/REVIEWER_RETURN_REQUIRED.json"
            review = json.loads(path.read_text(encoding="utf-8"))
            review["submission_confirmed"] = True
            review["decision"] = "REVIEWED_WITHOUT_CHANGES"
            path.write_text(json.dumps(review), encoding="utf-8")
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_INVALID, result["status"])
        finally:
            tmp.cleanup()

    def test_09_reviewed_without_changes_records_human_review_but_no_release(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            path, _ = self.complete_review(root)
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_RECORDED, result["status"])
            self.assertTrue(result["professional_review_recorded"])
            self.assertFalse(result["requires_recalculation"])
            self.assertEqual("NONE_AUTOMATIC", result["release_effect"])
        finally:
            tmp.cleanup()

    def test_10_reviewed_with_changes_requires_files(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            path, _ = self.complete_review(root, "REVIEWED_WITH_CHANGES")
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_INVALID, result["status"])
        finally:
            tmp.cleanup()

    def test_11_reviewed_with_changes_hashes_and_flags_changed_model(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            changed = root/"reviewed_model.esa"
            changed.write_bytes(b"CHANGED SCIA MODEL")
            path, review = self.complete_review(root, "REVIEWED_WITH_CHANGES")
            review["reviewed_replacement_files"] = [{
                "replaces_role": "SCIA_ESA",
                "path": changed.relative_to(root).as_posix(),
            }]
            path.write_text(json.dumps(review), encoding="utf-8")
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_RECORDED, result["status"])
            self.assertTrue(result["requires_recalculation"])
            self.assertEqual(["SCIA_ESA"], result["changed_roles"])
            self.assertTrue(result["returned_files"][0]["content_changed"])
        finally:
            tmp.cleanup()

    def test_12_fake_change_with_identical_content_is_rejected(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            replacement = root/"replacement.esa"
            replacement.write_bytes(b"SCIA MODEL")
            path, review = self.complete_review(root, "REVIEWED_WITH_CHANGES")
            review["reviewed_replacement_files"] = [{
                "replaces_role": "SCIA_ESA",
                "path": replacement.relative_to(root).as_posix(),
            }]
            path.write_text(json.dumps(review), encoding="utf-8")
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_INVALID, result["status"])
        finally:
            tmp.cleanup()

    def test_13_recalculation_required_never_releases(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            path, _ = self.complete_review(root, "RECALCULATION_REQUIRED")
            result = process_review_return(root, root/"dossier", path)
            self.assertEqual(RETURN_RECORDED, result["status"])
            self.assertTrue(result["requires_recalculation"])
            self.assertEqual("LOCKED", result["safety"]["production_release"])
            self.assertEqual("LOCKED", result["safety"]["for_construction_release"])
        finally:
            tmp.cleanup()

    def test_14_rejected_review_is_recorded_without_release(self):
        tmp, root = self.repo()
        try:
            create_dossier(plan(root), root)
            path, _ = self.complete_review(root, "REJECTED")
            result = process_review_return(root, root/"dossier", path)
            self.assertTrue(result["review_rejected"])
            self.assertEqual("NONE_AUTOMATIC", result["release_effect"])
        finally:
            tmp.cleanup()

    def test_15_hard_safety_boundaries(self):
        tmp, root = self.repo()
        try:
            result = create_dossier(plan(root), root)
            self.assertFalse(result["safety"]["automatic_professional_approval"])
            self.assertFalse(result["safety"]["automatic_code_compliance_claim"])
            self.assertEqual("LOCKED", result["safety"]["production_release"])
            self.assertEqual("LOCKED", result["safety"]["for_construction_release"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
