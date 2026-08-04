from __future__ import annotations
import unittest
from pathlib import Path

class GlobalSourcingBackwardCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[2]
        cls.sa = (repo / "phoenix" / "autonomy" / "session_adapters.py").read_text(encoding="utf-8")
        cls.sc = (repo / "phoenix" / "autonomy" / "structural_session_chain.py").read_text(encoding="utf-8")

    def test_01_cost_legacy_reason_code_still_exists(self):
        self.assertIn('"reason":"LOCAL_MATERIAL_AVAILABILITY_REQUIRED_FOR_COST_PLAN"', self.sa)

    def test_02_cost_legacy_json_keys_still_exist(self):
        self.assertIn('"local_material_selection_register":local_material_selection_ref', self.sa)
        self.assertIn('"local_material_availability_required":True', self.sa)

    def test_03_closure_legacy_reason_code_still_exists(self):
        self.assertIn('"reason":"LOCAL_MATERIAL_SUPPLY_GATE_NOT_PASSED"', self.sa)

    def test_04_structural_legacy_reason_codes_still_exist(self):
        self.assertIn('"LOCAL_STRUCTURAL_MATERIAL_AVAILABILITY_REQUIRED"', self.sc)
        self.assertIn('"STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED"', self.sc)

if __name__ == "__main__":
    unittest.main()
