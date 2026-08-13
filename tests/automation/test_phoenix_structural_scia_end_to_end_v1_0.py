from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.structural_scia_end_to_end_v1_0 import (
    BLOCKED_SEED,
    BLOCKED_SEED_SELECTION,
    READY_SCIA,
    SCIA_CALCULATED_VERIFICATION_REQUIRED,
    CROSS_VERIFIED_DOSSIER_REQUIRED,
    READY_REVIEW,
    inventory_esa_candidates,
    prepare,
    execute,
)


class E2ETests(unittest.TestCase):
    def repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        project = root / "projects/runtime/PHOENIX-PAT-001"
        (project / "inputs/structural").mkdir(parents=True)
        return tmp, root, project

    def test_01_no_seed_blocks_without_fabrication(self):
        tmp, root, project = self.repo()
        try:
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertEqual(BLOCKED_SEED, result["status"])
            self.assertIsNone(result["selected_seed"])
            self.assertFalse(result["safety"]["automatic_project_analysis_scope_decision"])
        finally:
            tmp.cleanup()

    def test_02_one_input_seed_is_auto_selected(self):
        tmp, root, project = self.repo()
        try:
            seed = project / "inputs/structural/scia/base_model.esa"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"ESA")
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertEqual(READY_SCIA, result["status"])
            self.assertTrue(str(result["selected_seed"]).endswith("base_model.esa"))
        finally:
            tmp.cleanup()

    def test_03_tied_seed_candidates_require_selection(self):
        tmp, root, project = self.repo()
        try:
            d = project / "inputs/structural/scia"
            d.mkdir(parents=True)
            (d/"base_a.esa").write_bytes(b"A")
            (d/"base_b.esa").write_bytes(b"B")
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertEqual(BLOCKED_SEED_SELECTION, result["status"])
            self.assertIsNone(result["selected_seed"])
        finally:
            tmp.cleanup()

    def test_04_result_or_review_seed_is_not_high_confidence(self):
        tmp, root, project = self.repo()
        try:
            d = project / "results/scia"
            d.mkdir(parents=True)
            (d/"working.esa").write_bytes(b"X")
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertEqual(BLOCKED_SEED_SELECTION, result["status"])
        finally:
            tmp.cleanup()

    def test_05_prepare_generates_exact_gap_registers(self):
        tmp, root, project = self.repo()
        try:
            prepare(root, "PHOENIX-PAT-001")
            w = project/"inputs/structural/scia_e2e_v1_0"
            self.assertTrue((w/"scia_e2e_control_REQUIRED.json").is_file())
            self.assertTrue((w/"scia_e2e_readiness.json").is_file())
            self.assertTrue((w/"scia_e2e_gap_register.json").is_file())
            self.assertTrue((w/"scia_e2e_evidence_inventory.json").is_file())
            self.assertTrue((w/"structural_independent_verification_plan_REQUIRED.json").is_file())
            self.assertTrue((w/"professional_dossier_plan_REQUIRED.json").is_file())
        finally:
            tmp.cleanup()

    def test_06_control_uses_lin_only_as_pipeline_baseline(self):
        tmp, root, project = self.repo()
        try:
            seed = project/"inputs/structural/scia/base.esa"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"X")
            prepare(root, "PHOENIX-PAT-001")
            control = json.loads((project/"inputs/structural/scia_e2e_v1_0/scia_e2e_control_REQUIRED.json").read_text())
            self.assertEqual("LIN", control["scia"]["analysis_type"])
            self.assertIn("pipeline baseline", control["scia"]["analysis_scope_note"])
            self.assertFalse(control["safety"]["automatic_project_analysis_scope_decision"])
        finally:
            tmp.cleanup()

    def test_07_prepare_does_not_generate_default_verification_tolerances(self):
        tmp, root, project = self.repo()
        try:
            prepare(root, "PHOENIX-PAT-001")
            p = json.loads((project/"inputs/structural/scia_e2e_v1_0/structural_independent_verification_plan_REQUIRED.json").read_text())
            serialized = json.dumps(p)
            self.assertNotIn('"absolute": 0.', serialized)
            self.assertNotIn('"relative": 0.', serialized)
            self.assertTrue(all(v["applicability"] == "INPUT_REQUIRED" for v in p["categories"].values()))
        finally:
            tmp.cleanup()

    def test_08_existing_nonempty_control_values_are_preserved(self):
        tmp, root, project = self.repo()
        try:
            w = project/"inputs/structural/scia_e2e_v1_0"
            w.mkdir(parents=True)
            (w/"scia_e2e_control_REQUIRED.json").write_text(json.dumps({
                "scia": {"input_xml": "projects/runtime/PHOENIX-PAT-001/inputs/structural/scia/input.xml"},
                "verification": {},
                "professional_dossier": {},
            }), encoding="utf-8")
            prepare(root, "PHOENIX-PAT-001")
            control = json.loads((w/"scia_e2e_control_REQUIRED.json").read_text())
            self.assertTrue(control["scia"]["input_xml"].endswith("input.xml"))
            self.assertFalse(control["automatic_professional_review"])
        finally:
            tmp.cleanup()

    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.execute_scia_plan")
    def test_09_live_scia_can_stop_at_verification_input_gate(self, scia_mock):
        tmp, root, project = self.repo()
        try:
            seed = project/"inputs/structural/scia/base.esa"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"X")
            prepare(root, "PHOENIX-PAT-001")
            scia_mock.return_value = {"status": "CALCULATED_UNVERIFIED", "safety": {}}
            result = execute(root, "PHOENIX-PAT-001", root/"fake.exe")
            self.assertEqual(SCIA_CALCULATED_VERIFICATION_REQUIRED, result["status"])
        finally:
            tmp.cleanup()

    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.run_verification_plan")
    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.execute_scia_plan")
    def test_10_cross_verified_can_stop_at_dossier_gate(self, scia_mock, verify_mock):
        tmp, root, project = self.repo()
        try:
            seed = project/"inputs/structural/scia/base.esa"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"X")
            verification_plan = project/"inputs/structural/custom_verification_plan.json"
            verification_plan.write_text("{}", encoding="utf-8")
            prepare(root, "PHOENIX-PAT-001")
            control_path = project/"inputs/structural/scia_e2e_v1_0/scia_e2e_control_REQUIRED.json"
            control = json.loads(control_path.read_text())
            control["verification"]["plan_path"] = verification_plan.relative_to(root).as_posix()
            control_path.write_text(json.dumps(control), encoding="utf-8")
            scia_mock.return_value = {"status": "CALCULATED_UNVERIFIED"}
            verify_mock.return_value = {"status": "TECHNICALLY_CROSS_VERIFIED"}
            result = execute(root, "PHOENIX-PAT-001", root/"fake.exe")
            self.assertEqual(CROSS_VERIFIED_DOSSIER_REQUIRED, result["status"])
        finally:
            tmp.cleanup()

    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.create_dossier")
    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.run_verification_plan")
    @patch("phoenix.autonomy.structural_scia_end_to_end_v1_0.execute_scia_plan")
    def test_11_full_machine_chain_stops_ready_for_human_review(self, scia_mock, verify_mock, dossier_mock):
        tmp, root, project = self.repo()
        try:
            seed = project/"inputs/structural/scia/base.esa"
            seed.parent.mkdir(parents=True)
            seed.write_bytes(b"X")
            verification_plan = project/"inputs/structural/custom_verification_plan.json"
            dossier_plan = project/"inputs/structural/custom_dossier_plan.json"
            verification_plan.write_text("{}", encoding="utf-8")
            dossier_plan.write_text("{}", encoding="utf-8")
            prepare(root, "PHOENIX-PAT-001")
            control_path = project/"inputs/structural/scia_e2e_v1_0/scia_e2e_control_REQUIRED.json"
            control = json.loads(control_path.read_text())
            control["verification"]["plan_path"] = verification_plan.relative_to(root).as_posix()
            control["professional_dossier"]["plan_path"] = dossier_plan.relative_to(root).as_posix()
            control_path.write_text(json.dumps(control), encoding="utf-8")
            scia_mock.return_value = {"status": "CALCULATED_UNVERIFIED"}
            verify_mock.return_value = {"status": "TECHNICALLY_CROSS_VERIFIED"}
            dossier_mock.return_value = {"status": "READY_FOR_PROFESSIONAL_REVIEW", "handoff_zip": "review.zip"}
            result = execute(root, "PHOENIX-PAT-001", root/"fake.exe")
            self.assertEqual(READY_REVIEW, result["status"])
            self.assertEqual("NOT_YET_RETURNED", result["professional_review_status"])
        finally:
            tmp.cleanup()

    def test_12_inventory_is_project_scoped(self):
        tmp, root, project = self.repo()
        try:
            outside = root/"somewhere/base.esa"
            outside.parent.mkdir()
            outside.write_bytes(b"OUT")
            self.assertEqual([], inventory_esa_candidates(root, "PHOENIX-PAT-001"))
        finally:
            tmp.cleanup()

    def test_13_release_locks_are_hard(self):
        tmp, root, project = self.repo()
        try:
            result = prepare(root, "PHOENIX-PAT-001")
            self.assertFalse(result["safety"]["automatic_professional_approval"])
            self.assertFalse(result["safety"]["automatic_code_compliance_claim"])
            self.assertFalse(result["safety"]["automatic_verification_tolerance_generation"])
            self.assertEqual("LOCKED", result["safety"]["production_release"])
            self.assertEqual("LOCKED", result["safety"]["for_construction_release"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
