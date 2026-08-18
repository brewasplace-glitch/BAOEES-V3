import unittest
from pathlib import Path
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=Path(__file__).resolve().parents[2]
  cls.js=(cls.r/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_open_source_player_robust_mount_activation_repair_v1_0.js").read_text(encoding="utf-8")
  cls.html=(cls.r/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
 def test_health_gate(self):
  self.assertIn('fetch(`${SIDECAR}/health`',self.js)
  self.assertIn('SIDECAR_UNHEALTHY',self.js)
 def test_robust_card_discovery(self):
  self.assertIn("findTvCard",self.js)
  self.assertIn('t.includes("de tv")',self.js)
  self.assertIn('t.includes("presentatie")',self.js)
 def test_mounts_real_sidecar(self):
  self.assertIn("127.0.0.1:8770",self.js)
  self.assertIn("phoenixOpenSourceMediaPlayer",self.js)
  self.assertIn("/player/?project=",self.js)
 def test_preserves_controls_and_hides_legacy_display(self):
  self.assertIn("findControlAnchor",self.js)
  self.assertIn("phoenixLegacyTvHidden",self.js)
 def test_mutation_recovery(self):
  self.assertIn("MutationObserver",self.js)
  self.assertIn("ensureMounted",self.js)
 def test_loaded_after_original_player_bridge(self):
  old="PROJECT_PHOENIX_de_tv_open_source_media_player_v1_0.js"
  new="PROJECT_PHOENIX_de_tv_open_source_player_robust_mount_activation_repair_v1_0.js"
  self.assertIn(old,self.html);self.assertIn(new,self.html)
  self.assertGreater(self.html.index(new),self.html.index(old))
if __name__=="__main__": unittest.main()
