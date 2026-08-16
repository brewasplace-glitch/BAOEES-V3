from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
JS = REPO / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "PROJECT_PHOENIX_de_tv_project_scoped_semantic_visual_routing_v1_0.js"

class TestPhoenixTVDirectVisualArtifactOpenRenderBridgeV10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding="utf-8-sig")

    def test_direct_carousel_bridge_is_present(self):
        self.assertIn("phoenixTvNext", self.js)
        self.assertIn("seekExactArtifact", self.js)
        self.assertIn("currentArtifactPath", self.js)
        self.assertIn("waitForMetaChange", self.js)

    def test_semantic_route_does_not_submit_path_to_legacy_parser(self):
        self.assertIn("do not forward a filesystem/artifact path to the legacy text parser", self.js)
        self.assertNotIn("input.value = `toon ${path}`", self.js)

    def test_exact_visual_artifact_paths_are_preserved(self):
        self.assertIn("phoenix_3d_viewer.html", self.js)
        self.assertIn("phoenix_automatic_video.avi", self.js)
        self.assertIn("site_plan.${dxf?'dxf':'svg'}", self.js)

    def test_authoritative_project_context_is_preserved(self):
        self.assertIn("'progressStep'", self.js)
        self.assertIn("'progressLabel'", self.js)
        self.assertIn("closest('#projectList')", self.js)
        self.assertIn("cross-project fallback is verboden", self.js)

    def test_command_normalization_is_preserved(self):
        self.assertIn(r"\bsituatie\s*tekening\b", self.js)
        self.assertIn(r"\bsituatietekening\b", self.js)
        self.assertIn("'viewer_3d'", self.js)
        self.assertIn("'auto_video'", self.js)

    def test_blank_svg_quality_gate_uses_direct_dxf_seek(self):
        self.assertIn("blankFraction", self.js)
        self.assertIn("0.0035", self.js)
        self.assertIn("seekExactArtifact(artifactFor(pid, 'site_plan', true))", self.js)

if __name__ == "__main__":
    unittest.main()
