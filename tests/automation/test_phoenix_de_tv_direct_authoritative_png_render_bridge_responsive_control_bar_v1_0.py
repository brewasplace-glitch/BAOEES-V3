import unittest
from pathlib import Path
class TestDirectPngResponsiveV10(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=Path(__file__).resolve().parents[2]
  cls.js=(cls.r/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_direct_authoritative_png_render_bridge_responsive_control_bar_v1_0.js").read_text(encoding="utf-8")
  cls.html=(cls.r/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
 def test_four_pngs(self):
  for x in ("phoenix_exterior_front.png","phoenix_exterior_rear.png","phoenix_bird_view.png","phoenix_interior_cutaway.png"): self.assertIn(x,self.js)
 def test_no_technical_playlist(self):
  for x in ("adapter_result.json","presentation_manifest.json","phoenix_walkthrough.html","phoenix_drivethrough.html"): self.assertNotIn(x,self.js)
 def test_direct_image_render(self):
  self.assertIn('document.createElement("img")',self.js); self.assertIn("object-fit:contain",self.js)
 def test_mask_release(self):
  self.assertIn("releaseMask()",self.js); self.assertIn('removeAttribute("aria-busy")',self.js)
 def test_responsive_height(self):
  self.assertIn("window.innerHeight-top-reserve",self.js); self.assertIn('window.addEventListener("resize",fit',self.js)
 def test_controls(self):
  for x in ("presentation","next","prev","show"): self.assertIn('"'+x+'"',self.js)
 def test_commands(self):
  for x in ("ontwerp|exterieur|variant b|3d","achterzijde|achtergevel|rear","vogelvlucht|bird view","interieur|interior"): self.assertIn(x,self.js)
 def test_loaded_last(self):
  n="PROJECT_PHOENIX_de_tv_direct_authoritative_png_render_bridge_responsive_control_bar_v1_0.js"
  a="PROJECT_PHOENIX_de_tv_authoritative_visual_media_router_v1_0.js"
  self.assertIn(n,self.html); self.assertGreater(self.html.index(n),self.html.index(a))
if __name__=="__main__": unittest.main()
