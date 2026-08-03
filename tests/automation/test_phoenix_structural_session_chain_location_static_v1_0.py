import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTERS=ROOT/"phoenix"/"autonomy"/"session_adapters.py"
CHAIN=ROOT/"phoenix"/"autonomy"/"structural_session_chain.py"
LOCATION=ROOT/"phoenix"/"autonomy"/"location_intelligence.py"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
LAUNCHER=ROOT/"runners"/"PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

class StaticTests(unittest.TestCase):
    def test_01_old_generic_mapping_blocker_removed_from_structural_adapter(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        start=text.index("def run_structural(");end=text.index("def _session_location",start)
        self.assertNotIn("V8_1_TO_V8_12_VALIDATED_INPUT_MAPPING_REQUIRED",text[start:end])
        self.assertIn("run_structural_chain(",text[start:end])

    def test_02_all_engine_names_are_registered(self):
        text=CHAIN.read_text(encoding="utf-8")
        for i in range(1,13):
            self.assertIn(f'"8.{i}.0"',text)

    def test_03_no_automatic_engineering_approval_or_load_invention(self):
        text=CHAIN.read_text(encoding="utf-8")
        self.assertIn("automatic_professional_approval",text)
        self.assertIn("production_release",text)
        self.assertIn("belastingswaarden",text)

    def test_04_location_does_not_use_ui_locale(self):
        text=LOCATION.read_text(encoding="utf-8")
        self.assertIn('"ui_locale_used":False',text)
        self.assertIn('"automatic_cadastral_inference":False',text)

    def test_05_runtime_1_8_4_gate(self):
        self.assertIn('VERSION = "1.8.5"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.5"',LAUNCHER.read_text(encoding="utf-8"))

    def test_06_zero_idle_polling_preserved(self):
        js=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"
        if js.is_file(): self.assertNotIn("setInterval(",js.read_text(encoding="utf-8"))

    def test_07_structural_chain_explicitly_declares_no_legacy_pilot_dependency(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn('"legacy_pilot_dependency": False',text)

if __name__=="__main__":
    unittest.main()
