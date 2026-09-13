import unittest
from pathlib import Path

class TestStartscreenIdleStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]
        cls.js=(root/"phoenix/local_app/static/official_start_v3_0/phoenix_detv_cad_bridge.js").read_text(encoding="utf-8")

    def test_intrusive_global_observer_removed(self):
        self.assertNotIn("characterData:true",self.js)
        self.assertNotIn("observer.observe(document.documentElement",self.js)
        self.assertNotIn("setInterval(health",self.js)
        self.assertNotIn(".focus(",self.js)
        self.assertNotIn("window.focus",self.js)

    def test_bounded_observer_disconnects(self):
        self.assertIn("bootstrapObserver.disconnect()",self.js)
        self.assertIn("observer-timeout",self.js)
        self.assertIn("cad-controls-mounted",self.js)
        self.assertIn("bootstrapObserver.observe(root,{childList:true,subtree:true})",self.js)

    def test_background_work_pauses_when_hidden(self):
        self.assertIn('document.addEventListener("visibilitychange"',self.js)
        self.assertIn("document.hidden",self.js)
        self.assertIn("hiddenHealthSkips",self.js)
        self.assertIn("scheduleHealth(60000)",self.js)

    def test_working_cad_chain_is_preserved(self):
        for needle in (
            "__PHOENIX_DETV_CAD_HARD_MOUNT_V1__",
            "hardMountViewer",
            "phoenix-cad-file-loaded",
            "Open CAD bestand",
            'const SIDECAR="http://127.0.0.1:8765"',
        ):
            self.assertIn(needle,self.js)

if __name__=="__main__":
    unittest.main()
