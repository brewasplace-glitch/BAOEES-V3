import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ACQ=ROOT/"phoenix/autonomy/real_world_data_acquisition.py"
HTML=ROOT/"phoenix/autonomy/public_html_source_integration.py"
SITE=ROOT/"phoenix/autonomy/site_parcel_intelligence.py"
MAT=ROOT/"phoenix/autonomy/local_material_supply_intelligence.py"
CHAIN=ROOT/"phoenix/autonomy/structural_session_chain.py"
DRAW=ROOT/"phoenix/autonomy/drawing_production.py"
SERVER=ROOT/"phoenix/local_app/server.py"
LAUNCHER=ROOT/"runners/PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"
REG=ROOT/"configs/phoenix/real_world_data_source_registry_v1_0.json"

class StaticTests(unittest.TestCase):
    def test_01_suriname_sources_are_explicitly_configured(self):
        reg=json.loads(REG.read_text(encoding="utf-8"));ids={x["provider_id"] for x in reg["providers"]}
        self.assertIn("SR_BESTBUY_CEMENT_PRICES",ids);self.assertIn("SR_VABI_BLOCKS_PRICES",ids);self.assertIn("SR_SUBEMA_READY_MIX_CAPABILITY",ids);self.assertIn("SR_GOV_BUILDING_LAWS",ids)
        self.assertIn("SR_KULDIPSINGH_BUILDING_MATERIALS",ids)
        self.assertIn("SR_KULDIPSINGH_BUILDING_PRICES",ids)
        self.assertIn("SR_KULDIPSINGH_READYMIX_CAPABILITY",ids)
        self.assertIn("SR_KULDIPSINGH_PRECAST_PRESTRESSED_CAPABILITY",ids)
    def test_02_live_sources_disabled_in_test_mode(self):
        text=ACQ.read_text(encoding="utf-8");self.assertIn("PHOENIX_TEST_MODE",text);self.assertIn("TEST_MODE_LIVE_FETCH_DISABLED",text)
    def test_03_no_implicit_web_search(self):
        text=ACQ.read_text(encoding="utf-8");self.assertIn('"web_search_used":False',text);self.assertIn("html_regulatory_reference",text)
    def test_04_pdf_vector_scale_parser_present(self):
        text=SITE.read_text(encoding="utf-8");self.assertIn("page.get_drawings()",text);self.assertIn("EXPLICIT_DRAWING_SCALE",text);self.assertIn("PyMuPDF",text)
    def test_05_commercial_and_engineering_material_gates_are_separate(self):
        text=MAT.read_text(encoding="utf-8");self.assertIn("all_requirements_commercially_available",text);self.assertIn("all_structural_requirements_engineering_qualified",text)
        self.assertIn("all_structural_requirements_engineering_qualified",CHAIN.read_text(encoding="utf-8"))
    def test_06_north_arrow_false_pass_removed(self):
        text=DRAW.read_text(encoding="utf-8");self.assertIn("NOORDRICHTING NIET GEVALIDEERD",text)
    def test_07_runtime_1_8_7_gate(self):
        self.assertIn('VERSION = "1.8.7"',SERVER.read_text(encoding="utf-8"));self.assertIn('value.get("version") != "1.8.7"',LAUNCHER.read_text(encoding="utf-8"))
    def test_08_zero_idle_polling_preserved(self):
        js=ROOT/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"
        if js.is_file():self.assertNotIn("setInterval(",js.read_text(encoding="utf-8"))
if __name__=="__main__":unittest.main()
