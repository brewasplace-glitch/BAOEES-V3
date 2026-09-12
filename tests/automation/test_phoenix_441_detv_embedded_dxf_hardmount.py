import unittest
from pathlib import Path

class TestHardMount(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[2]
        self.bridge=(root/"phoenix/local_app/static/official_start_v3_0/phoenix_detv_cad_bridge.js").read_text(encoding="utf-8")
        self.viewer=(root/"phoenix/detv_cad_bridge/assets/viewer.html").read_text(encoding="utf-8")

    def test_bridge_mounts_inside_detv(self):
        self.assertIn("findDeTvViewport",self.bridge)
        self.assertIn("phoenix-cad-detv-mount",self.bridge)
        self.assertIn("DE_TV_PANEL_FALLBACK",self.bridge)
        self.assertNotIn("phoenix-cad-modal",self.bridge)

    def test_ready_file_loaded_protocol(self):
        self.assertIn("phoenix-cad-viewer-ready",self.bridge)
        self.assertIn("sendPendingFile",self.bridge)
        self.assertIn('event.origin!==SIDECAR',self.bridge)
        self.assertIn('e.data.protocol==="v1"',self.viewer)
        self.assertIn("phoenix-cad-file-loaded",self.viewer)

    def test_compact_view(self):
        self.assertIn('document.documentElement.classList.add("compact")',self.viewer)
        self.assertIn("preserveAspectRatio",self.viewer)
        self.assertIn("ALLOWED_PARENT_ORIGINS",self.viewer)

if __name__=="__main__":
    unittest.main()
