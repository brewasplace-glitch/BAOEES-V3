from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
START = ROOT / "phoenix" / "local_app" / "static" / "official_start_v3_0"
INDEX = START / "index.html"
LAYER = START / "PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js"
PHASE18 = ROOT / "phoenix" / "autonomy" / "integrated_project_orchestration.py"

class Phoenix4619StartscreenConsolidationR1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8-sig")
        cls.layer = LAYER.read_text(encoding="utf-8")
        cls.phase18 = PHASE18.read_text(encoding="utf-8")

    def test_01_single_tv_authority_preserved(self):
        self.assertEqual(self.html.count('id="phoenixTvPanel"'), 1)
        self.assertIn("DE TV", self.html)

    def test_02_user_navigation_contract(self):
        self.assertIn('data-module="new_project"', self.html)
        self.assertIn('data-module="projects"', self.html)
        self.assertIn('id="resultsNav"', self.html)
        self.assertIn('id="phoenixManageNav"', self.html)

    def test_03_technical_navigation_hidden_by_layer(self):
        for item in (
            "digital_twin", "ai_agents", "simulations",
            "documents", "reports", "asset_management", "dashboard"
        ):
            self.assertIn(f'"{item}"', self.layer)
        self.assertIn("button.hidden = true", self.layer)

    def test_04_capability_registry_preserved_but_governed(self):
        self.assertIn("phoenix-start-capability-drawer", self.layer)
        self.assertIn("drawer.hidden = !managementOpen", self.layer)

    def test_05_modules_and_workflows_preserved_but_governed(self):
        self.assertIn("phoenixModulesPanel", self.layer)
        self.assertIn("phoenixWorkflowsPanel", self.layer)

    def test_06_phase18_none_is_null_safe(self):
        self.assertIn(
            'selected = str(project.get("selected_variant_id") or "").strip()',
            self.phase18,
        )

    def test_07_known_visible_mojibake_removed_from_index(self):
        for token in ("Ã¢Ã…â€™â€š", "Ã¢Ã…â€™Ã‹Å“", "Ã¢Ã…â€œÂ¦", "Ã°Ã…Â¸Ã…Â½Â¤", "Ã¢â€ºÂ¶"):
            self.assertNotIn(token, self.html)

    def test_08_consolidation_layer_loaded(self):
        self.assertIn(
            "PROJECT_PHOENIX_startscreen_consolidation_v4_6_19.js?v=1.0.0",
            self.html,
        )

if __name__ == "__main__":
    unittest.main()