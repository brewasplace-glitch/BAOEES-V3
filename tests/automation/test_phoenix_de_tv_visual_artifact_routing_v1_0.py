import unittest
from phoenix.autonomy.tv_visual_artifact_routing_v1_0 import *
class T(unittest.TestCase):
 def test_json(self): self.assertTrue(is_technical_evidence("x/auto_video_manifest.json"))
 def test_visual(self): self.assertTrue(is_visual_artifact("drawings/site_plan.svg"));self.assertTrue(is_drawing_artifact("drawings/site_plan.dxf"))
 def test_order(self):
  x=order_presentable_artifacts(["a/manifest.json","drawings/site_plan.dxf","drawings/site_plan.svg"])
  self.assertTrue(x[0].endswith(".svg"));self.assertTrue(x[-1].endswith(".json"))
if __name__=="__main__":unittest.main()
