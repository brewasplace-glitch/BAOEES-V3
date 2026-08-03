import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTERS=ROOT/"phoenix"/"autonomy"/"session_adapters.py"
CHAIN=ROOT/"phoenix"/"autonomy"/"structural_session_chain.py"
PROFILE=ROOT/"phoenix"/"autonomy"/"structural_profile.py"
ENGINE=ROOT/"phoenix"/"autonomy"/"local_material_supply_intelligence.py"
SERVER=ROOT/"phoenix"/"local_app"/"server.py"
LAUNCHER=ROOT/"runners"/"PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

class LocalMaterialStaticTests(unittest.TestCase):
    def test_01_architecture_generates_material_selection_register(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("build_local_material_supply_context",text)
        self.assertIn("local_material_selection_register.json",text)
        self.assertIn("material_product_change_control.json",text)

    def test_02_structural_chain_has_local_material_solver_gate(self):
        text=CHAIN.read_text(encoding="utf-8")
        self.assertIn("LOCAL_STRUCTURAL_MATERIAL_AVAILABILITY_REQUIRED",text)
        self.assertIn("STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED",text)

    def test_03_cost_plan_requires_local_material_selection(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("LOCAL_MATERIAL_AVAILABILITY_REQUIRED_FOR_COST_PLAN",text)

    def test_04_release_gate_checks_local_material_supply(self):
        text=ADAPTERS.read_text(encoding="utf-8")
        self.assertIn("LOCAL_MATERIAL_SUPPLY_GATE_NOT_PASSED",text)

    def test_05_profile_contains_material_policy(self):
        text=PROFILE.read_text(encoding="utf-8")
        self.assertIn("REQUIRES_LOCAL_MATERIAL_SUPPLY_INTELLIGENCE",text)
        self.assertIn("material_substitution_requires_recalculation",text)

    def test_06_import_is_not_local_and_substitution_is_not_automatic(self):
        text=ENGINE.read_text(encoding="utf-8")
        self.assertIn('"automatic_import_approval":False',text)
        self.assertIn('"automatic_product_substitution":False',text)
        self.assertIn('"recalculation_required_if_substituted":True',text)

    def test_07_runtime_1_8_5_gate(self):
        self.assertIn('VERSION = "1.8.7"',SERVER.read_text(encoding="utf-8"))
        self.assertIn('value.get("version") != "1.8.7"',LAUNCHER.read_text(encoding="utf-8"))

    def test_08_zero_idle_polling_preserved(self):
        js=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"
        if js.is_file():
            self.assertNotIn("setInterval(",js.read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
