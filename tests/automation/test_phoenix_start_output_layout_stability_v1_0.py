import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = ROOT / "phoenix/local_app/static/official_start_v3_0/index.html"
CSS = ROOT / "phoenix/local_app/static/official_start_v3_0/phoenix_output_layout_stability.css"
JS = ROOT / "phoenix/local_app/static/official_start_v3_0/phoenix_output_layout_stability.js"

class StartOutputLayoutStabilityTests(unittest.TestCase):
    def test_assets_exist(self):
        self.assertTrue(INDEX.exists())
        self.assertTrue(CSS.exists())
        self.assertTrue(JS.exists())

    def test_index_loads_assets_once(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertEqual(text.count("phoenix_output_layout_stability.css"), 1)
        self.assertEqual(text.count("phoenix_output_layout_stability.js"), 1)

    def test_desired_output_layout_contract(self):
        js = JS.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("GEWENSTE OUTPUT", js)
        self.assertIn("MIJN STANDAARD", js)
        self.assertIn("AUTONOME PHOENIX-FLOW", js)
        self.assertIn('row.append(standardCard, flowCard)', js)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", css)

    def test_pointer_stability_has_no_pointer_driven_dom_loop(self):
        js = JS.read_text(encoding="utf-8")
        self.assertNotIn("mousemove", js)
        self.assertNotIn("pointermove", js)
        self.assertNotIn("mouseover", js)
        self.assertNotIn("MutationObserver", js)
        self.assertNotIn("setInterval", js)
        self.assertIn("window.setTimeout(tryOnce, 150)", js)

    def test_hover_geometry_is_stable(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("@media (hover: hover) and (pointer: fine)", css)
        self.assertIn("transform: none !important", css)
        self.assertIn("filter: none !important", css)
        self.assertIn("will-change: auto !important", css)
        self.assertNotIn("transition: all", css)

    def test_legacy_start_contracts_are_preserved(self):
        text = INDEX.read_text(encoding="utf-8")
        combined = text + "\n" + "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in INDEX.parent.glob("*.js")
        )
        self.assertIn("X-Phoenix-Token", combined)
        self.assertIn("architectural_orchestration", combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
