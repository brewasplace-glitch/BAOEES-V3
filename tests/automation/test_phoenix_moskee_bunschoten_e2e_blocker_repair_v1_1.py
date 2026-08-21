
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BINDING = ROOT / "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"
CANONICAL = ROOT / "configs/projects/moskee_bunschoten.json"
RUNNER = ROOT / "phoenix/validation/moskee_bunschoten_real_project_e2e_v1_0.py"

class MoskeeE2EBlockerRepairTests(unittest.TestCase):
    def test_binding_and_canonical_exist(self):
        self.assertTrue(CANONICAL.is_file())
        self.assertTrue(BINDING.is_file())

    def test_binding_has_unique_top_level_identity(self):
        data = json.loads(BINDING.read_text(encoding="utf-8"))
        self.assertEqual(data["project_id"], "MOSKEE-BUNSCHOTEN-E2E-REAL-001")
        self.assertTrue(data.get("project_name"))

    def test_binding_records_canonical_source(self):
        data = json.loads(BINDING.read_text(encoding="utf-8"))
        meta = data["metadata"]["phoenix_real_project_e2e_binding"]
        self.assertEqual(meta["canonical_project_file"], "configs/projects/moskee_bunschoten.json")
        self.assertTrue(meta["production_locked"])
        self.assertTrue(meta["for_construction_locked"])

    def test_runner_uses_execution_binding_not_unlaunchable_root(self):
        src = RUNNER.read_text(encoding="utf-8")
        self.assertIn('CANONICAL_PROJECT_FILE="configs/projects/moskee_bunschoten.json"', src)
        self.assertIn('PROJECT_FILE="configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"', src)

    def test_catalog_and_plan_accept_binding(self):
        from phoenix.local_app.architectural_orchestration_runtime import ArchitecturalOrchestrationRuntime
        runtime = ArchitecturalOrchestrationRuntime(ROOT)
        entries = [p for p in runtime.project_catalog() if p["file"] == "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["project_id"], "MOSKEE-BUNSCHOTEN-E2E-REAL-001")
        plan = runtime.plan("configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json")
        self.assertEqual(plan["project_id"], "MOSKEE-BUNSCHOTEN-E2E-REAL-001")
        self.assertEqual(plan["project_file"], "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json")

    def test_video_evidence_contract_remains_enabled(self):
        src = RUNNER.read_text(encoding="utf-8")
        self.assertIn("record_video_dir", src)
        self.assertIn("trace.zip", src)

    def test_release_locks_remain(self):
        src = RUNNER.read_text(encoding="utf-8")
        self.assertIn("PRODUCTION_RELEASE=LOCKED", src)
        self.assertIn("FOR_CONSTRUCTION=LOCKED", src)

if __name__ == "__main__":
    unittest.main(verbosity=2)
