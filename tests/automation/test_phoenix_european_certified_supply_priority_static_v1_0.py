from __future__ import annotations
import unittest
from pathlib import Path

class EuropeanCertifiedSupplyPriorityStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo=Path(__file__).resolve().parents[2]
        cls.gms=(repo/"phoenix"/"autonomy"/"global_material_sourcing.py").read_text(encoding="utf-8")
        cls.policy=(repo/"configs"/"phoenix"/"european_certified_supply_priority_policy_v1_0.json").read_text(encoding="utf-8")

    def test_01_european_sort_hook(self):
        self.assertIn("import_sort_key", self.gms)
        self.assertIn("european_certified_supply_priority", self.gms)

    def test_02_ready_mix_gate(self):
        self.assertIn("ready_mix_import_allowed", self.gms)

    def test_03_landed_cost_primary(self):
        self.assertIn("LOWEST_COMPLETE_LANDED_COST", self.policy)
        self.assertIn("STRICTLY_LOWER_COMPLETE_LANDED_COST", self.policy)

    def test_04_ordering_payment_disabled(self):
        lower=self.policy.lower()
        self.assertIn('"automatic_ordering": false', lower)
        self.assertIn('"automatic_payment": false', lower)

if __name__ == "__main__":
    unittest.main()
