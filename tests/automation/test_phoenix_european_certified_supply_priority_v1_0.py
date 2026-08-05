from __future__ import annotations
import unittest
from phoenix.autonomy.european_certified_supply_priority import (
    origin_priority,
    import_sort_key,
    ready_mix_import_allowed,
    european_discovery_queries,
)

class EuropeanCertifiedSupplyPriorityTests(unittest.TestCase):
    def row(self, country, cost, lead=30):
        return {
            "origin_country_code": country,
            "lead_time_days": lead,
            "landed_cost": {"status": "PASSED", "landed_cost_per_unit_srd": cost},
        }

    def test_01_nl_be_eu_priority(self):
        self.assertLess(origin_priority("NL"), origin_priority("BE"))
        self.assertLess(origin_priority("BE"), origin_priority("DE"))
        self.assertLess(origin_priority("DE"), origin_priority("CN"))

    def test_02_equal_cost_prefers_nl(self):
        rows = [self.row("CN",100), self.row("DE",100), self.row("BE",100), self.row("NL",100)]
        rows.sort(key=import_sort_key)
        self.assertEqual("NL", rows[0]["origin_country_code"])

    def test_03_non_eu_wins_if_strictly_cheaper(self):
        rows = [self.row("NL",101), self.row("CN",100)]
        rows.sort(key=import_sort_key)
        self.assertEqual("CN", rows[0]["origin_country_code"])

    def test_04_queries_are_europe_first(self):
        q = european_discovery_queries("B500B rebar supplier", "reinforcement_steel")
        self.assertIn("Netherlands", q[0])
        self.assertIn("Belgium", q[1])
        self.assertIn("European Union", q[2])
        self.assertEqual("B500B rebar supplier", q[-1])

    def test_05_ready_mix_import_blocks_without_explicit_evidence(self):
        c = {"description":"Ready-mix concrete C25/30","product_form":"READY_MIX"}
        self.assertFalse(ready_mix_import_allowed(c, "structural_concrete"))

    def test_06_ready_mix_import_needs_source_reference(self):
        c = {"description":"Ready-mix concrete C25/30","explicit_importability_evidence":True}
        self.assertFalse(ready_mix_import_allowed(c, "structural_concrete"))
        c["importability_source_reference"]="projects/runtime/P1/sources/importability.json"
        self.assertTrue(ready_mix_import_allowed(c, "structural_concrete"))

if __name__ == "__main__":
    unittest.main()
