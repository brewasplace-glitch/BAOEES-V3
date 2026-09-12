import tempfile,unittest
from pathlib import Path
from phoenix.detv_cad_bridge import patcher
from phoenix.detv_cad_bridge.server import render_svg,viewer_page
class T(unittest.TestCase):
 def test_patch(self):
  h="<html><body><h1>PROJECT PHOENIX DE TV</h1></body></html>"; self.assertGreaterEqual(patcher.score_candidate("apps/dashboard/index.html",h),25)
  p=patcher.inject_host_text(h); self.assertEqual(patcher.inject_host_text(p).count(patcher.BEGIN),1)
 def test_viewer(self):
  with tempfile.TemporaryDirectory() as td:
   repo=Path(td); (repo/"phoenix/detv_cad_bridge/assets").mkdir(parents=True)
   src=Path(__file__).resolve().parents[2]/"phoenix/detv_cad_bridge/assets/viewer.html"; (repo/"phoenix/detv_cad_bridge/assets/viewer.html").write_bytes(src.read_bytes())
   h=viewer_page(repo,"x","file","P"); self.assertIn("Open bestand",h); self.assertIn("Open in LibreCAD",h)
 def test_svg(self):
  import ezdxf
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"x.dxf"; d=ezdxf.new("R2010"); d.layers.add("TEST_LAYER"); d.modelspace().add_line((0,0),(10,10),dxfattribs={"layer":"TEST_LAYER"}); d.saveas(p)
   r=render_svg(p); self.assertIn("<svg",r["svg"]); self.assertIn("TEST_LAYER",r["layers"])
if __name__=="__main__": unittest.main()
