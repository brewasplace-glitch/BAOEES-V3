import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_action_load_model_generation_v8_2_0.py"
PROJECT_CONFIG = ROOT / "configs" / "projects" / "generic_building_structural_action_load_model_v8_2_0.json"
ENGINE_CONFIG = ROOT / "configs" / "phoenix" / "structural" / "structural_action_load_model_generation_v8_2_0.json"

spec = importlib.util.spec_from_file_location("phoenix_struct_action_load_v8_2_0", RUNNER_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class TestStructuralActionLoadModelGenerationV820(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
        cls.engine_cfg = json.loads(ENGINE_CONFIG.read_text(encoding="utf-8"))
        cls.model = module.build_action_load_model(cls.payload)

    def test_engine_identity(self):
        self.assertEqual(self.model["engine"]["version"], "8.2.0")
        self.assertEqual(self.engine_cfg["version"], "8.2.0")

    def test_load_cases_and_categories_generated(self):
        self.assertEqual(self.model["summary"]["load_case_count"], 3)
        self.assertEqual(self.model["category_counts"], {"permanent": 1, "variable": 1, "wind": 1})

    def test_self_weight_is_solver_flag_not_invented_numeric_weight(self):
        self_weight = [a for a in self.model["action_assignments"] if a["kind"] == "self_weight"]
        self.assertEqual(len(self_weight), 1)
        self.assertEqual(self_weight[0]["derivation"], "SOLVER_SELF_WEIGHT_FLAG")
        self.assertNotIn("magnitude", self_weight[0])
        self.assertEqual(len(self_weight[0]["target_element_ids"]), 4)

    def test_area_and_line_assignments_generated(self):
        self.assertEqual(self.model["summary"]["action_assignment_count"], 5)
        floor_assignments = [a for a in self.model["action_assignments"] if a["source_action_id"] == "ACT-Q-FLOOR"]
        wind_assignments = [a for a in self.model["action_assignments"] if a["source_action_id"] == "ACT-W-X"]
        self.assertEqual(len(floor_assignments), 1)
        self.assertEqual(len(wind_assignments), 2)

    def test_explicit_combinations_preserved(self):
        self.assertEqual(self.model["summary"]["load_combination_count"], 2)
        uls = next(c for c in self.model["load_combinations"] if c["id"] == "COMB-ULS-01")
        self.assertEqual(uls["limit_state"], "ULS")
        self.assertEqual([t["coefficient"] for t in uls["terms"]], [1.35, 1.5, 1.5])

    def test_units_and_action_basis(self):
        self.assertEqual(self.model["unit_system"]["force"], "kN")
        self.assertEqual(self.model["action_basis"]["values_source"], "EXPLICIT_PROJECT_INPUT")
        self.assertFalse(self.model["action_basis"]["automatic_normative_value_invention"])

    def test_traceability_and_digital_twin_contract(self):
        self.assertIn("ACT-G-SW", self.model["traceability"])
        self.assertGreaterEqual(len(self.model["traceability"]["ACT-G-SW"]), 1)
        self.assertTrue(self.model["digital_twin_writeback"]["enabled"])
        self.assertEqual(self.model["digital_twin_writeback"]["approval_state"], "CANDIDATE_ONLY")

    def test_unknown_target_is_reported_without_fake_assignment(self):
        payload = json.loads(json.dumps(self.payload))
        payload["action_load_input"]["actions"].append({
            "id": "ACT-UNKNOWN",
            "case_id": "LC-Q",
            "category": "variable",
            "kind": "line",
            "direction": "GLOBAL_Z",
            "magnitude": -1.0,
            "target": {"element_ids": ["M9999"]},
        })
        model = module.build_action_load_model(payload)
        unknown_assignments = [a for a in model["action_assignments"] if a["source_action_id"] == "ACT-UNKNOWN"]
        self.assertEqual(unknown_assignments, [])
        self.assertTrue(any("M9999" in warning for warning in model["warnings"]))

    def test_release_safety(self):
        release = self.model["release"]
        self.assertFalse(release["automatic_structural_approval"])
        self.assertFalse(release["analysis_execution_allowed"])
        self.assertEqual(release["structural_model_release"], "LOCKED")
        self.assertTrue(release["engineering_review_required"])


if __name__ == "__main__":
    unittest.main()
