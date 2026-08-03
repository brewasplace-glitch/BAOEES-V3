import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
CTX=ROOT/"phoenix/autonomy/project_context.py"
PROFILE=ROOT/"phoenix/autonomy/structural_profile.py"
DRAW=ROOT/"phoenix/autonomy/drawing_production.py"
ADAPTERS=ROOT/"phoenix/autonomy/session_adapters.py"
ORCH=ROOT/"phoenix/autonomy/session_orchestrator.py"
SERVER=ROOT/"phoenix/local_app/server.py"
LAUNCHER=ROOT/"runners/PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"
LOCALIZER=ROOT/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_frontend_nl_v1_0_0.js"

class StaticTests(unittest.TestCase):
    def test_01_context_engine_never_uses_ui_locale_as_project_country(self):
        t=CTX.read_text(encoding="utf-8")
        self.assertNotIn("frontend_locale",t)
        self.assertNotIn("nl-NL",t)

    def test_02_structural_profile_does_not_define_design_loads_or_code(self):
        t=PROFILE.read_text(encoding="utf-8")
        self.assertIn('"status":"NOT_DEFINED_BY_THIS_GENERATOR"',t)
        self.assertIn('"standard":None',t)
        self.assertIn('"automatic_structural_approval":False',t)

    def test_03_drawings_are_concept_and_site_false_pass_is_blocked(self):
        t=DRAW.read_text(encoding="utf-8")
        self.assertIn("CONCEPT_FOR_REVIEW",t)
        self.assertIn("SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN",t)
        self.assertIn('"production_release":"LOCKED"',t)

    def test_04_architecture_adapter_wires_all_three_engines(self):
        t=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("generate_project_context",t)
        self.assertIn("generate_structural_project_profile",t)
        self.assertIn("produce_architectural_drawings",t)

    def test_05_orchestrator_v1_3_and_runtime_v1_8_2(self):
        self.assertIn('VERSION = "1.3.0"',ORCH.read_text(encoding="utf-8"))
        self.assertIn('VERSION = "1.8.4"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.4"',LAUNCHER.read_text(encoding="utf-8"))

    def test_06_zero_idle_polling_preserved(self):
        js=(ROOT/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js").read_text(encoding="utf-8")
        self.assertNotIn("setInterval(",js)

    def test_07_dutch_site_fact_blocker_reason_added(self):
        self.assertIn("SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN",LOCALIZER.read_text(encoding="utf-8"))

if __name__=="__main__":unittest.main()
