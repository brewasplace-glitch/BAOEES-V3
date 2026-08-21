from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"
CONFIG = ROOT / "configs/phoenix/autonomous_project_orchestrator_v1_0.json"

TOKENS = [
    "calculations",
    "structural_drawings",
    "foundation_drawings",
    "structural_analysis",
    "foundation_design",
]

class MoskeeStructuralCapabilityActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = json.loads(BINDING.read_text(encoding="utf-8"))
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_all_structural_tokens_present_once(self):
        requested = [str(x) for x in self.binding["requested_outputs"]]
        for token in TOKENS:
            self.assertEqual(requested.count(token), 1, token)

    def test_all_tokens_map_to_structural_engineering(self):
        output_map = self.config["output_capability_map"]
        for token in TOKENS:
            self.assertIn("structural_engineering", output_map[token], token)

    def test_structural_capability_is_adapter_ready(self):
        cap = self.config["capabilities"]["structural_engineering"]
        self.assertEqual(cap["execution_mode"], "adapter")
        self.assertTrue(cap["session_adapter_ready"])

    def test_structural_dependencies_preserved(self):
        deps = set(self.config["capabilities"]["structural_engineering"]["depends_on"])
        self.assertEqual(deps, {"architecture", "digital_twin"})

    def test_structural_runner_exists(self):
        cap = self.config["capabilities"]["structural_engineering"]
        runners = [ROOT / x for x in cap["runner_candidates"]]
        self.assertTrue(any(x.is_file() for x in runners))

    def test_activation_metadata_is_fail_safe(self):
        meta = self.binding["metadata"]["phoenix_structural_capability_activation"]
        self.assertEqual(meta["route"], "structural_engineering")
        self.assertEqual(meta["production_release"], "LOCKED")
        self.assertEqual(meta["for_construction"], "LOCKED")

    def test_binding_retains_nonresidential_route(self):
        route = self.binding["metadata"]["phoenix_architectural_engine_route"]["route"]
        self.assertEqual(route, "NONRESIDENTIAL_REUSE_V1")

if __name__ == "__main__":
    unittest.main(verbosity=2)
