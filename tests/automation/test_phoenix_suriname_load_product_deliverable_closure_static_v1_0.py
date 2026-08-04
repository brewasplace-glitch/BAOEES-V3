import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "phoenix" / "autonomy" / "session_adapters.py"
ORCH = ROOT / "phoenix" / "autonomy" / "session_orchestrator.py"
BASELINE = ROOT / "phoenix" / "autonomy" / "minimum_deliverable_baseline.py"
LOAD = ROOT / "phoenix" / "autonomy" / "suriname_structural_load_basis.py"
PRODUCT = ROOT / "phoenix" / "autonomy" / "local_product_qualification.py"


class StaticTests(unittest.TestCase):
    def test_01_architecture_prepares_product_overlay_before_material_selection(self):
        text = ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("prepare_local_product_qualification_overlay(", text)
        self.assertLess(text.index("prepare_local_product_qualification_overlay("), text.index("build_local_material_supply_context("))

    def test_02_structural_prepares_suriname_load_basis_before_chain(self):
        text = ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("ensure_suriname_structural_load_basis(", text)
        self.assertLess(text.index("ensure_suriname_structural_load_basis("), text.index("run_structural_chain("))

    def test_03_minimum_baseline_resolves_real_artifact_evidence(self):
        text = BASELINE.read_text(encoding="utf-8")
        self.assertIn("build_minimum_deliverable_manifest(ctx)", text)

    def test_04_desired_output_false_pass_guard_is_integrated(self):
        text = ORCH.read_text(encoding="utf-8")
        self.assertIn("validate_desired_output_evidence(", text)
        self.assertIn('"evidence_validation": evidence_validation', text)
        self.assertIn("DESIRED_OUTPUT_ARTIFACT_REQUIRED", text)

    def test_05_load_policy_does_not_claim_current_law_or_auto_approval(self):
        text = LOAD.read_text(encoding="utf-8")
        self.assertIn('"verified_as_current_law": False', text)
        self.assertIn('"automatic_professional_approval": False', text)
        self.assertIn('"included": False', text)

    def test_06_product_qualification_does_not_invent_availability_or_grade(self):
        text = PRODUCT.read_text(encoding="utf-8")
        self.assertIn('"invented_availability": False', text)
        self.assertIn('"invented_strength_class": False', text)
        self.assertIn("Only one explicit grade qualifies", text)


if __name__ == "__main__":
    unittest.main()
