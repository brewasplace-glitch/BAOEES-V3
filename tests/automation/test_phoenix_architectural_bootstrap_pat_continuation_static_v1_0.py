import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTERS=ROOT/'phoenix'/'autonomy'/'session_adapters.py'
ORCH=ROOT/'phoenix'/'autonomy'/'session_orchestrator.py'
JS=ROOT/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js'
LOCALIZER=ROOT/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'PROJECT_PHOENIX_frontend_nl_v1_0_0.js'
SERVER=ROOT/'phoenix'/'local_app'/'server.py'
LAUNCHER=ROOT/'runners'/'PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py'
class StaticTests(unittest.TestCase):
    def test_01_adapter_calls_autonomous_bootstrap(self):
        t=ADAPTERS.read_text(encoding='utf-8'); self.assertIn('generate_architectural_bootstrap',t); self.assertIn('AUTONOMOUS_TEXT_BOOTSTRAP',t)
    def test_02_orchestrator_uses_output_coverage(self):
        t=ORCH.read_text(encoding='utf-8'); self.assertIn('adapter_output_coverage',t); self.assertIn('desired_output_states',t); self.assertIn('VERSION = "1.3.0"',t)
    def test_03_pat_defect_004_modal_sync(self):
        t=JS.read_text(encoding='utf-8'); self.assertIn('updateAutonomousRunModal(job)',t); self.assertIn('autonomousRunStatus',t); self.assertIn('autonomousRunBlockers',t)
    def test_04_no_idle_interval_added(self):
        self.assertNotIn('setInterval(',JS.read_text(encoding='utf-8'))
    def test_05_dutch_new_blocker_reasons(self):
        t=LOCALIZER.read_text(encoding='utf-8'); self.assertIn('SITE_CONTEXT_REQUIRED',t); self.assertIn('FINAL_DRAWING_EXPORT_REQUIRED',t)
    def test_06_runtime_1_8_2_gate(self):
        self.assertIn('VERSION = "1.8.4"',SERVER.read_text(encoding='utf-8')); self.assertIn('value.get("version") != "1.8.4"',LAUNCHER.read_text(encoding='utf-8'))
if __name__=='__main__': unittest.main()
