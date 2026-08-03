import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ORCH=ROOT/"phoenix"/"autonomy"/"session_orchestrator.py"
ADAPTERS=ROOT/"phoenix"/"autonomy"/"session_adapters.py"
CONFIG=ROOT/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
LAUNCHER=ROOT/"runners"/"PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

class SessionAdapterStaticTests(unittest.TestCase):
    def test_01_orchestrator_executes_adapters(self):
        text=ORCH.read_text(encoding="utf-8")
        self.assertIn("def _run_adapter(",text)
        self.assertIn("--expect-session-adapted",text)
        self.assertIn("adapter_result.json",text)

    def test_02_result_index_is_granular(self):
        text=ORCH.read_text(encoding="utf-8")
        self.assertIn("desired_output_states",text)
        self.assertIn("passed_outputs",text)
        self.assertIn("blocked_outputs",text)

    def test_03_all_seven_capabilities_have_generic_adapter_runner(self):
        cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
        for cap in ("architecture","digital_twin","structural_engineering","permit","cost_planning","reporting","closure"):
            item=cfg["capabilities"][cap]
            self.assertTrue(item["session_adapter_ready"])
            self.assertIn("session_adapter_",item["runner_candidates"][0])

    def test_04_no_idle_polling_regression(self):
        js=(ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js").read_text(encoding="utf-8")
        self.assertNotIn("setInterval(",js)

    def test_05_runtime_is_1_8_2(self):
        self.assertIn('VERSION = "1.8.6"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.6"',LAUNCHER.read_text(encoding="utf-8"))

    def test_06_release_stays_locked(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn('"production_release":"LOCKED"',text)
        self.assertIn('"automatic_professional_approval":False',text)

    def test_07_session_orchestrator_single_final_newline(self):
        raw=ORCH.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))

    def test_08_masterpack_core_has_no_trailing_whitespace(self):
        for path in (ORCH,ADAPTERS,SERVER,LAUNCHER):
            for index,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
                self.assertEqual(line.rstrip(" \t"),line,f"{path}:{index}")

if __name__=="__main__":
    unittest.main()
