import unittest
from pathlib import Path
import importlib.util

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]
        cls.server=(cls.repo/"phoenix/media_player/local_media_player_server_v1_0.py").read_text(encoding="utf-8")
        cls.player=(cls.repo/"phoenix/media_player/web/player.js").read_text(encoding="utf-8")
        cls.bridge=(cls.repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_open_source_media_player_v1_0.js").read_text(encoding="utf-8")
        cls.html=(cls.repo/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")

    def test_safe_media_roots_and_traversal_guard(self):
        self.assertIn("ALLOWED_ROOTS",self.server)
        self.assertIn("candidate.relative_to(root)",self.server)
        self.assertIn("PermissionError",self.server)

    def test_local_media_endpoint(self):
        self.assertIn("u.path=='/media'",self.server)
        self.assertIn("Content-Type",self.server)
        self.assertIn("Cache-Control",self.server)

    def test_player_owns_tv_tasks(self):
        for token in ("PRESENTATIE","VOLGENDE","VORIGE","VOL SCHERM","TOON"):
            self.assertIn(token,(cls:=self).__class__.repo.joinpath("phoenix/media_player/web/index.html").read_text(encoding="utf-8"))

    def test_pat002_visual_playlist(self):
        for name in ("phoenix_exterior_front.png","phoenix_exterior_rear.png","phoenix_bird_view.png","phoenix_interior_cutaway.png"):
            self.assertIn(name,self.player)
        self.assertNotIn("adapter_result.json",self.player)
        self.assertNotIn("presentation_manifest.json",self.player)

    def test_commands(self):
        for token in ("ontwerp|exterieur|variant b|3d","achterzijde|achtergevel|rear","vogelvlucht|bird view","interieur|interior"):
            self.assertIn(token,self.player)

    def test_bridge_mounts_sidecar(self):
        self.assertIn("127.0.0.1:8770/player/",self.bridge)
        self.assertIn("phoenixOpenSourceMediaPlayer",self.bridge)

    def test_index_loads_new_engine_last(self):
        n="PROJECT_PHOENIX_de_tv_open_source_media_player_v1_0.js"
        self.assertIn(n,self.html)
        self.assertGreater(self.html.index(n),self.html.index("PROJECT_PHOENIX_de_tv_seek_exact_visual_ready_bridge_loading_failsafe_v1_0.js"))

    def test_xibo_sdk_package_contract(self):
        pkg=(self.repo/"phoenix/media_player/xibo_sdk/package.json").read_text(encoding="utf-8")
        self.assertIn('"@xiboplayer/renderer": "0.7.23"',pkg)
        self.assertIn('"@xiboplayer/proxy": "0.7.23"',pkg)

if __name__=="__main__":
    unittest.main()
