import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class PersistenceContractTests(unittest.TestCase):
    def test_policy_targets_project_runtime(self):
        data=json.loads((ROOT/"configs/phoenix/real_world_evidence_persistence_policy_v1_0.json").read_text(encoding="utf-8"))
        self.assertEqual(data["runtime_evidence_root"],"projects/runtime/<project_id>/sources")
        self.assertTrue(data["rules"]["cross_project_source_leakage_forbidden"])

    def test_acquisition_destination_is_project_runtime(self):
        text=(ROOT/"phoenix/autonomy/real_world_data_acquisition.py").read_text(encoding="utf-8")
        self.assertIn('repository/"projects"/"runtime"/project_id/"sources"/category',text)

    def test_material_reader_is_project_specific(self):
        text=(ROOT/"phoenix/autonomy/local_material_supply_intelligence.py").read_text(encoding="utf-8")
        self.assertIn('"PROJECT_RUNTIME_MATERIAL_SUPPLY"',text)
        self.assertIn('_discover_catalogs(repository,policy,project_id)',text)

    def test_cost_reader_is_project_specific(self):
        text=(ROOT/"phoenix/autonomy/local_cost_intelligence.py").read_text(encoding="utf-8")
        self.assertIn('"PROJECT_RUNTIME_MARKET_PRICES"',text)
        self.assertIn('_discover_ratebooks(repository,policy,project_id)',text)

    def test_structural_load_reader_is_project_specific(self):
        text=(ROOT/"phoenix/autonomy/structural_action_load_basis.py").read_text(encoding="utf-8")
        self.assertIn('repository/"projects"/"runtime"/project_id/"sources"/"structural_action_load"',text)

if __name__=="__main__":
    unittest.main()
