from __future__ import annotations
import unittest
from pathlib import Path

class GlobalMaterialSourcingStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[2]
        cls.sa = (cls.repo / "phoenix" / "autonomy" / "session_adapters.py").read_text(encoding="utf-8")
        cls.sc = (cls.repo / "phoenix" / "autonomy" / "structural_session_chain.py").read_text(encoding="utf-8")
        cls.dr = (cls.repo / "phoenix" / "autonomy" / "deliverable_evidence_resolver.py").read_text(encoding="utf-8")
        cls.gms = (cls.repo / "phoenix" / "autonomy" / "global_material_sourcing.py").read_text(encoding="utf-8")

    def test_01_architecture_runs_global_sourcing(self):
        self.assertIn("build_global_material_sourcing_context", self.sa)
        self.assertIn("structural_material_selection_register.json", self.sa)

    def test_02_structural_accepts_merged_supply_but_preserves_reason_contracts(self):
        self.assertIn("structural_material_selection_register.json", self.sa)
        self.assertIn("LOCAL_STRUCTURAL_MATERIAL_AVAILABILITY_REQUIRED", self.sc)
        self.assertIn("STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED", self.sc)
        self.assertIn("qualified_engineering_ids", self.sc)

    def test_03_cost_accepts_local_or_imported_supply_with_legacy_aliases(self):
        self.assertIn("LOCAL_MATERIAL_AVAILABILITY_REQUIRED_FOR_COST_PLAN", self.sa)
        self.assertIn("local_material_selection_register", self.sa)
        self.assertIn("local_or_imported_material_supply_required", self.sa)
        self.assertIn("IMPORTED_MATERIAL_LANDED_COST_EVIDENCE_REQUIRED", self.sa)

    def test_04_closure_preserves_legacy_reason_code_on_merged_supply_gate(self):
        self.assertIn("LOCAL_MATERIAL_SUPPLY_GATE_NOT_PASSED", self.sa)
        self.assertIn("all_requirements_supply_confirmed", self.sa)

    def test_05_deliverable_material_evidence_uses_merged_register(self):
        self.assertIn('structural_material_selection_register.json', self.dr)

    def test_06_no_automatic_ordering_or_fabricated_cost_components(self):
        self.assertIn('"automatic_ordering": False', self.gms)
        self.assertIn("CUSTOMS_DUTY_EVIDENCE_REQUIRED", self.gms)
        self.assertIn("IMPORT_TAX_EVIDENCE_REQUIRED", self.gms)
        self.assertIn("CURRENT_FX_EVIDENCE_REQUIRED", self.gms)

    def test_07_configured_https_only_no_implicit_search(self):
        self.assertIn("global_material_source_urls", self.gms)
        self.assertIn('"implicit_web_search_used": False', self.gms)

if __name__ == "__main__":
    unittest.main()
