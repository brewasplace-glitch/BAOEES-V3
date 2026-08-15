from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
JS = REPO / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "PROJECT_PHOENIX_de_tv_project_scoped_semantic_visual_routing_v1_0.js"

class TestPhoenixTVAuthoritativeContextCommandNormalizationV10R1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding="utf-8-sig")

    def test_authoritative_progress_context(self):
        self.assertIn("'progressStep'", self.js)
        self.assertIn("'progressLabel'", self.js)
        self.assertIn("authoritativeActiveProjectId", self.js)

    def test_catalog_excluded_as_active_project_source(self):
        self.assertIn("closest('#projectList')", self.js)
        self.assertIn("Never infer the active project from #projectList", self.js)

    def test_command_normalization_variants(self):
        self.assertIn("normalizeCommand", self.js)
        self.assertIn(r"\bsituatie\s*tekening\b", self.js)
        self.assertIn(r"\bsituatietekening\b", self.js)
        self.assertIn(r"\bsite\s*plan\b", self.js)

    def test_visual_semantics(self):
        self.assertIn("phoenix_3d_viewer.html", self.js)
        self.assertIn("phoenix_automatic_video.avi", self.js)

    def test_quality_gate(self):
        self.assertIn("blankFraction", self.js)
        self.assertIn("0.0035", self.js)

    def test_backward_compatible_contract_markers(self):
        self.assertIn("site_plan.${dxf?'dxf':'svg'}", self.js)
        self.assertIn("cross-project fallback is verboden", self.js)

if __name__ == "__main__":
    unittest.main()
