import unittest
from pathlib import Path

class TestPhoenixTvVisualOnlyPresentationV10(unittest.TestCase):
    def test_contract_filters_technical_artifacts(self):
        repo=Path(__file__).resolve().parents[2]
        js=(repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js").read_text(encoding="utf-8")
        self.assertIn('p.endsWith(".json")',js)
        self.assertIn("manifest",js)
        self.assertIn("technical(item.path)",js)
        self.assertIn('b.id==="phoenixTvPresentation"',js)

    def test_pat002_real_blender_visuals_are_primary(self):
        repo=Path(__file__).resolve().parents[2]
        js=(repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js").read_text(encoding="utf-8")
        for name in (
          "phoenix_exterior_front.png",
          "phoenix_exterior_rear.png",
          "phoenix_bird_view.png",
          "phoenix_interior_cutaway.png",
        ):
            self.assertIn(name,js)

    def test_internal_seek_is_visually_masked(self):
        repo=Path(__file__).resolve().parents[2]
        js=(repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js").read_text(encoding="utf-8")
        self.assertIn('s.style.visibility="hidden"',js)
        self.assertIn("clearLoading()",js)
        self.assertIn("Visuele output laden",js)

    def test_start_screen_load_order(self):
        repo=Path(__file__).resolve().parents[2]
        html=(repo/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
        visual="PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js"
        strict="PROJECT_PHOENIX_strict_requested_output_presentation_contract_v1_0.js"
        pat="PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js"
        self.assertIn(visual,html)
        self.assertGreater(html.index(visual),html.index(strict))
        self.assertGreater(html.index(visual),html.index(pat))

if __name__=="__main__":
    unittest.main()
