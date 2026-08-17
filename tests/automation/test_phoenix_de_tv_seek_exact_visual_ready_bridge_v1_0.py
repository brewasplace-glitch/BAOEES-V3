import unittest
from pathlib import Path

class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=Path(__file__).resolve().parents[2]
  cls.js=(cls.r/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_de_tv_seek_exact_visual_ready_bridge_loading_failsafe_v1_0.js").read_text(encoding="utf-8")
  cls.html=(cls.r/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
 def test_uses_existing_seek_exact_bridge(self):
  self.assertIn('typeof r.seekExactArtifact!=="function"',self.js)
  self.assertIn("r.seekExactArtifact(path)",self.js)
 def test_no_guessed_direct_http_routes(self):
  for x in ("/artifact?path=","/api/artifact?path=","/api/file?path=","/files/"): self.assertNotIn(x,self.js)
 def test_visual_ready_gate(self):
  self.assertIn("function visualReady",self.js)
  self.assertIn('querySelector("img,canvas,video,iframe,svg,object,embed")',self.js)
  self.assertIn("waitForVisual",self.js)
 def test_hard_timeouts(self):
  self.assertIn("8000",self.js); self.assertIn("7000",self.js)
  self.assertIn("visual-ready timeout",self.js)
 def test_mask_always_released(self):
  self.assertIn("function release",self.js)
  self.assertIn('st.style.visibility=""',self.js)
  self.assertIn('removeAttribute("aria-busy")',self.js)
 def test_four_pngs(self):
  for x in ("phoenix_exterior_front.png","phoenix_exterior_rear.png","phoenix_bird_view.png","phoenix_interior_cutaway.png"): self.assertIn(x,self.js)
 def test_responsive_lower_height(self):
  self.assertIn("Math.min(560",self.js)
  self.assertIn("reserve=210",self.js)
 def test_loaded_after_previous_direct_bridge(self):
  a="PROJECT_PHOENIX_de_tv_direct_authoritative_png_render_bridge_responsive_control_bar_v1_0.js"
  b="PROJECT_PHOENIX_de_tv_seek_exact_visual_ready_bridge_loading_failsafe_v1_0.js"
  self.assertIn(a,self.html);self.assertIn(b,self.html);self.assertGreater(self.html.index(b),self.html.index(a))

if __name__=="__main__": unittest.main()
