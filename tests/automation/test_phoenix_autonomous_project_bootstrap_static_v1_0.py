import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
JS=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
REGISTRY=ROOT/"phoenix"/"local_app"/"workflow_registry.py"

class AutonomousStaticContractTests(unittest.TestCase):
    def test_01_autonomous_api_used(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn("/api/autonomous/start",js)

    def test_02_autonomous_mode_no_manual_workflow_selection(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('if(state.projectMode === "autonomous")',js)
        self.assertIn("Er is geen technische workflowselectie",js)

    def test_03_hidden_workflow_filtered(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn("filter(w => !w.ui_hidden)",js)

    def test_04_zero_idle_polling_preserved(self):
        js=JS.read_text(encoding="utf-8")
        self.assertNotIn("setInterval(",js)

    def test_05_server_has_autonomous_route(self):
        server=SERVER.read_text(encoding="utf-8")
        self.assertIn('"/api/autonomous/start"',server)
        self.assertIn("start_autonomous_session",server)

    def test_06_registry_supports_context_args(self):
        text=REGISTRY.read_text(encoding="utf-8")
        self.assertIn("extra_args",text)
        self.assertIn('return_code == 10',text)
        self.assertIn('job.status = "BLOCKED"',text)

    def test_07_no_pilot_path_in_generic_runner(self):
        runner=(ROOT/"runners"/"PROJECT_PHOENIX_autonomous_session_orchestrator_v1_0_0.py").read_text(encoding="utf-8")
        self.assertNotIn("BB35_pilot_1",runner)

if __name__=="__main__":
    unittest.main()
