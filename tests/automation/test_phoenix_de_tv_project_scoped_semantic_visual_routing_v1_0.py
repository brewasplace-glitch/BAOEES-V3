from pathlib import Path
import unittest
REPO=Path(__file__).resolve().parents[2]
JS=REPO/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'PROJECT_PHOENIX_de_tv_project_scoped_semantic_visual_routing_v1_0.js'
INDEX=REPO/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'index.html'
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.js=JS.read_text(encoding='utf-8-sig'); cls.html=INDEX.read_text(encoding='utf-8-sig')
 def test_paths(self):
  self.assertIn('phoenix_3d_viewer.html',self.js);self.assertIn('phoenix_automatic_video.avi',self.js);self.assertIn("site_plan.${dxf?'dxf':'svg'}",self.js)
 def test_scope(self):
  self.assertIn('CROSS-PROJECT ROUTING GEBLOKKEERD',self.js);self.assertIn('cross-project fallback is verboden',self.js)
 def test_quality(self):
  self.assertIn('blankFraction',self.js);self.assertIn('0.0035',self.js);self.assertIn('Project-eigen DXF wordt geopend',self.js)
 def test_loaded_after_v1(self):
  a='PROJECT_PHOENIX_de_tv_visual_artifact_routing_v1_0.js';b='PROJECT_PHOENIX_de_tv_project_scoped_semantic_visual_routing_v1_0.js'
  self.assertIn(a,self.html);self.assertIn(b,self.html);self.assertLess(self.html.index(a),self.html.index(b))
if __name__=='__main__': unittest.main()
