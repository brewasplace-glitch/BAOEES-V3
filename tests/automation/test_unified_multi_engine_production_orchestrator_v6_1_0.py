from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/phoenix/unified_multi_engine_production_orchestrator_v6_1_0.json"
PROJECT = ROOT / "configs/projects/moskee_bunschoten_multi_engine_pilot_v6_1_0.json"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_unified_multi_engine_production_orchestrator_v6_1_0.py"


class ProductionOrchestratorConfigTests(unittest.TestCase):
    def test_six_engine_routes(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(cfg["engine_routing"]), 6)
        self.assertFalse(
            cfg["qualification_dependency"]["simulated_results_allowed"]
        )
        self.assertTrue(cfg["digital_twin"]["single_source_of_truth"])

    def test_release_policy(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = cfg["release_policy"]
        self.assertTrue(policy["all_required_phases_pass"])
        self.assertTrue(policy["all_artifacts_sha256_hashed"])
        self.assertFalse(policy["simulated_results_allowed"])
        self.assertTrue(policy["professional_review_required"])


class PilotProjectTests(unittest.TestCase):
    def test_moskee_pilot_geometry(self):
        project = json.loads(PROJECT.read_text(encoding="utf-8"))
        scope = project["scope"]
        calculated = (
            scope["building_extension_width_m"]
            * scope["building_extension_length_m"]
            * scope["storeys"]
        )
        self.assertEqual(calculated, scope["gross_floor_area_m2"])
        self.assertEqual(scope["gross_floor_area_m2"], 140.0)

    def test_all_six_engines_required(self):
        project = json.loads(PROJECT.read_text(encoding="utf-8"))
        required = [
            engine
            for engine, task in project["engine_tasks"].items()
            if task["required"]
        ]
        self.assertEqual(len(required), 6)


class OrchestratorRunnerTests(unittest.TestCase):
    def test_runner_is_valid_python(self):
        ast.parse(RUNNER.read_text(encoding="utf-8"))

    def test_runner_requires_qualification_gate(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("qualify_engines", text)
        self.assertIn("qualified_engines", text)
        self.assertIn("production_release", text)

    def test_runner_builds_central_digital_twin_and_handoffs(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("build_digital_twin", text)
        self.assertIn("create_engine_plan", text)
        self.assertIn("create_handoffs", text)
        self.assertIn("artifact_manifest.json", text)
        self.assertIn("PRODUCTION ORCHESTRATION GATE: UNLOCKED", text)

    def test_permit_ready_remains_blocked(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"permit_ready": False', text)
        self.assertIn(
            "PERMIT-READY RELEASE: BLOCKED PENDING PROFESSIONAL EVIDENCE",
            text,
        )


if __name__ == "__main__":
    unittest.main()
