import unittest
from pathlib import Path

class TestPhoenixTvAuthoritativeVisualMediaRouterV10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]
        cls.js=(cls.repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_authoritative_visual_media_router_v1_0.js").read_text(encoding="utf-8")
        cls.html=(cls.repo/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")

    def test_window_capture_owns_tv_controls(self):
        self.assertIn('window.addEventListener("click",captureClick,true)',self.js)
        self.assertIn('window.addEventListener("keydown",captureKey,true)',self.js)
        self.assertIn("ev.stopImmediatePropagation()",self.js)

    def test_pat002_catalog_contains_only_four_blender_visuals(self):
        for name in (
            "phoenix_exterior_front.png",
            "phoenix_exterior_rear.png",
            "phoenix_bird_view.png",
            "phoenix_interior_cutaway.png",
        ):
            self.assertIn(name,self.js)
        # Legacy schematic presentation files must not be hardwired into the authoritative PAT-002 catalog.
        for forbidden in (
            "phoenix_walkthrough.html",
            "phoenix_drivethrough.html",
            "phoenix_auto_video_presentation.html",
            "presentation_manifest.json",
            "adapter_result.json",
        ):
            self.assertNotIn(forbidden,self.js)

    def test_technical_artifact_filter_is_fail_closed(self):
        for token in (
            "json|txt|log|csv|xml",
            "manifest|evidence|adapter_result|project_state|digital_twin",
            "technical(item.path)",
        ):
            self.assertIn(token,self.js)

    def test_commands_are_centrally_resolved(self):
        for command in (
            "toon ontwerp",
            "toon exterieur",
            "toon variant b",
            "toon 3d",
            "toon interieur",
            "toon vogelvlucht",
            "toon achterzijde",
            "toon achtergevel",
        ):
            self.assertIn(f'["{command}"',self.js)
        self.assertIn("resolveCommand(input.value)",self.js)
        self.assertIn("handleCommand(input.value)",self.js)

    def test_exact_known_visual_path_is_supported(self):
        self.assertIn('replace(/^toon\\s+/i,"")',self.js)
        self.assertIn("const exact=cat.find",self.js)
        self.assertIn("const leaf=path.split",self.js)

    def test_prev_next_presentation_share_authoritative_catalog(self):
        self.assertIn("STATE.catalog=buildCatalog()",self.js)
        self.assertIn("startPresentation()",self.js)
        self.assertIn("openIndex(STATE.index+1)",self.js)
        self.assertIn("openIndex(STATE.index-1)",self.js)

    def test_internal_seek_is_masked(self):
        self.assertIn('s.style.visibility="hidden"',self.js)
        self.assertIn("Visuele output laden",self.js)
        self.assertIn("unmask()",self.js)

    def test_load_order_is_last_tv_layer(self):
        authoritative="PROJECT_PHOENIX_de_tv_authoritative_visual_media_router_v1_0.js"
        previous="PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js"
        pat="PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js"
        self.assertIn(authoritative,self.html)
        self.assertGreater(self.html.index(authoritative),self.html.index(previous))
        self.assertGreater(self.html.index(authoritative),self.html.index(pat))

if __name__=="__main__":
    unittest.main()
