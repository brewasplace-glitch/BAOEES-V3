import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "configs/phoenix/real_project_e2e_validation_policy_v1_0.json"
PROBE = ROOT / "phoenix/validation/real_project_e2e_readiness.py"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_real_project_e2e_readiness_v1_0.ps1"

class RealProjectE2EReadinessTests(unittest.TestCase):
    def test_files_exist(self):
        self.assertTrue(POLICY.exists())
        self.assertTrue(PROBE.exists())
        self.assertTrue(RUNNER.exists())

    def test_primary_and_fallback_are_open_source(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(data["browser_evidence"]["primary"]["engine"], "Playwright")
        self.assertEqual(data["browser_evidence"]["primary"]["license"], "Apache-2.0")
        self.assertEqual(data["browser_evidence"]["fallback"]["engine"], "Selenium WebDriver")
        self.assertEqual(data["browser_evidence"]["fallback"]["license"], "Apache-2.0")

    def test_visual_evidence_is_not_json(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        gates = data["visual_gates"]
        self.assertTrue(gates["json_is_not_visual_proof"])
        self.assertTrue(gates["blank_visual_fails"])
        self.assertTrue(gates["project_scope_required"])

    def test_project_selection_is_not_silent(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertFalse(data["selection"]["auto_select"])

    def test_release_stays_locked(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(data["release"]["production_release"], "LOCKED")
        self.assertEqual(data["release"]["for_construction"], "LOCKED")

    def test_probe_checks_visual_stability_markers(self):
        source = PROBE.read_text(encoding="utf-8")
        self.assertIn("PERIODIC_VISUAL_HEARTBEAT_6S=REMOVED", source)
        self.assertIn("POINTER_RELEASE_GUARD=ENABLED", source)
        self.assertIn("DE_TV_CORE_UNCHANGED=PASS", source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
