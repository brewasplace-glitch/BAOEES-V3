import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTERS=ROOT/"phoenix"/"autonomy"/"session_adapters.py"
CHAIN=ROOT/"phoenix"/"autonomy"/"structural_session_chain.py"
ACQ=ROOT/"phoenix"/"autonomy"/"real_world_data_acquisition.py"
SITE=ROOT/"phoenix"/"autonomy"/"site_parcel_intelligence.py"
LOAD=ROOT/"phoenix"/"autonomy"/"structural_action_load_basis.py"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
LAUNCHER=ROOT/"runners"/"PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

class EngineeringRealWorldStaticTests(unittest.TestCase):
    def test_01_architecture_calls_real_world_acquisition_before_material_gate(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("acquire_real_world_data(",text)
        self.assertIn("analyze_site_drawings(",text)
        self.assertLess(text.index("acquire_real_world_data("),text.index("build_local_material_supply_context("))

    def test_02_structural_chain_uses_real_world_action_load_basis(self):
        text=CHAIN.read_text(encoding="utf-8")
        self.assertIn("build_structural_action_load_basis(",text)
        self.assertIn("CURRENT_STRUCTURAL_ACTION_LOAD_BASIS_REQUIRED",text)

    def test_03_acquisition_is_https_only_and_no_implicit_web_search(self):
        text=ACQ.read_text(encoding="utf-8")
        self.assertIn("Only HTTPS remote real-world sources are allowed",text)
        self.assertIn('"web_search_used":False',text)

    def test_04_site_engine_forbids_cadastral_false_pass(self):
        text=SITE.read_text(encoding="utf-8")
        self.assertIn('"cadastral_validation":False',text)
        self.assertIn("DWG_TO_DXF_CONVERSION_REQUIRED",text)

    def test_05_action_load_engine_does_not_invent_norm_values(self):
        text=LOAD.read_text(encoding="utf-8")
        self.assertIn('"automatic_norm_value_invention":False',text)
        self.assertIn('"automatic_combination_factor_invention":False',text)

    def test_06_runtime_1_8_6_gate(self):
        self.assertIn('VERSION = "1.8.6"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.6"',LAUNCHER.read_text(encoding="utf-8"))

    def test_07_zero_idle_polling_preserved(self):
        js=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"
        if js.is_file():self.assertNotIn("setInterval(",js.read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
