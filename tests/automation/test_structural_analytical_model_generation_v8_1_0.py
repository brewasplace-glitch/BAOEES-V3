import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_analytical_model_generation_v8_1_0.py"
PROJECT_CONFIG = ROOT / "configs" / "projects" / "generic_building_structural_analytical_model_v8_1_0.json"
ENGINE_CONFIG = ROOT / "configs" / "phoenix" / "structural" / "structural_analytical_model_generation_v8_1_0.json"

spec = importlib.util.spec_from_file_location("phoenix_struct_analytical_v8_1_0", RUNNER_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class TestStructuralAnalyticalModelGenerationV810(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
        cls.engine_cfg = json.loads(ENGINE_CONFIG.read_text(encoding="utf-8"))
        cls.model = module.build_analytical_model(cls.payload)

    def test_engine_identity(self):
        self.assertEqual(self.model["engine"]["version"], "8.1.0")
        self.assertEqual(self.engine_cfg["version"], "8.1.0")

    def test_nodes_and_members_generated(self):
        self.assertGreaterEqual(self.model["summary"]["node_count"], 6)
        self.assertEqual(self.model["summary"]["member_count"], 4)

    def test_shell_panels_generated(self):
        self.assertEqual(self.model["summary"]["shell_count"], 2)
        self.assertTrue(all(s["approval_state"] == "CANDIDATE_ONLY" for s in self.model["shells"]))

    def test_support_candidates_generated(self):
        self.assertEqual(self.model["summary"]["support_candidate_count"], 2)
        self.assertTrue(all(s["approval_state"] == "CANDIDATE_ONLY" for s in self.model["support_candidates"]))

    def test_connectivity_and_load_path(self):
        self.assertTrue(self.model["connectivity"])
        self.assertEqual(self.model["load_path_graph"]["mode"], "TOPOLOGICAL_ONLY")
        self.assertGreater(len(self.model["load_path_graph"]["edges"]), 0)

    def test_material_and_section_candidates(self):
        self.assertGreaterEqual(len(self.model["material_candidates"]), 6)
        self.assertEqual(len(self.model["section_candidates"]), 4)

    def test_traceability_and_digital_twin_contract(self):
        self.assertIn("COL-C01", self.model["traceability"])
        self.assertTrue(self.model["digital_twin_writeback"]["enabled"])
        self.assertEqual(self.model["digital_twin_writeback"]["approval_state"], "CANDIDATE_ONLY")

    def test_release_safety(self):
        self.assertFalse(self.model["release"]["automatic_structural_approval"])
        self.assertEqual(self.model["release"]["structural_model_release"], "LOCKED")
        self.assertTrue(self.model["release"]["engineering_review_required"])


if __name__ == "__main__":
    unittest.main()
