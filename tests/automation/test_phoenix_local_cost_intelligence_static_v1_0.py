import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTERS=ROOT/"phoenix"/"autonomy"/"session_adapters.py"
ENGINE=ROOT/"phoenix"/"autonomy"/"local_cost_intelligence.py"
NL=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_frontend_nl_v1_0_0.js"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
LAUNCHER=ROOT/"runners"/"PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

class LocalCostStaticTests(unittest.TestCase):
    def test_01_cost_adapter_uses_local_market_context(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("build_local_cost_market_context",text)
        self.assertIn("local_cost_market_context.json",text)
        self.assertIn("local_cost_price_source_register.json",text)

    def test_02_old_generic_ratebook_gate_removed_from_cost_function(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        start=text.index("def run_cost_planning")
        end=text.index("def run_reporting",start)
        block=text[start:end]
        self.assertNotIn("RATEBOOK_REQUIRED",block)
        self.assertNotIn('rglob("*ratebook*.json")',block)

    def test_03_no_silent_fx_or_tax(self):
        text=ENGINE.read_text(encoding="utf-8")
        self.assertIn('"international_reference_fallback_allowed":False',text)
        self.assertIn('"automatic_tax_application":False',text)
        self.assertIn('"fx_used":False',text)

    def test_04_dutch_reasons_present(self):
        text=NL.read_text(encoding="utf-8")
        self.assertIn("CURRENT_LOCAL_MARKET_PRICE_DATA_REQUIRED",text)
        self.assertIn("LOCAL_MARKET_PRICE_DATA_STALE",text)
        self.assertIn("LOCAL_MARKET_PRICE_CURRENCY_MISMATCH",text)

    def test_05_runtime_1_8_3_gate(self):
        self.assertIn('VERSION = "1.8.5"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.5"',LAUNCHER.read_text(encoding="utf-8"))

    def test_06_zero_idle_polling_preserved(self):
        js=(ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js")
        if js.is_file():
            self.assertNotIn("setInterval(",js.read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
