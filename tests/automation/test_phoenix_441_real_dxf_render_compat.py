import tempfile,unittest
from pathlib import Path

from phoenix.detv_cad_bridge import server

class TestRealDxfRenderCompatibility(unittest.TestCase):
    def test_svg_and_primitive_pipeline(self):
        import ezdxf
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"beam.dxf"
            d=ezdxf.new("R2010")
            d.layers.add("STEEL",color=5)
            d.layers.add("BOLTS",color=1)
            m=d.modelspace()
            m.add_line((0,0),(300,0),dxfattribs={"layer":"STEEL"})
            m.add_line((0,160),(300,160),dxfattribs={"layer":"STEEL"})
            for x in (40,260):
                for y in (30,60,100,130):
                    m.add_circle((x,y),8,dxfattribs={"layer":"BOLTS"})
            m.add_text("UB 305x165x40 WEB CONNECTION",dxfattribs={"height":12}).set_placement((10,180))
            d.saveas(p)

            s=server.render_svg_resilient(p)
            self.assertIn("<svg",s["svg"])
            self.assertTrue(s["renderer"].startswith("EZDXF_"))

            f=server.extract_browser_primitives(p)
            self.assertGreaterEqual(len(f["browser_primitives"]),11)
            self.assertEqual(f["renderer"],"PHOENIX_BROWSER_PRIMITIVE_CANVAS")

    def test_viewer_contains_canvas_fallback(self):
        root=Path(__file__).resolve().parents[2]
        html=(root/"phoenix/detv_cad_bridge/assets/viewer.html").read_text(encoding="utf-8")
        self.assertIn("renderPrimitiveCanvas",html)
        self.assertIn("browser_primitives",html)
        self.assertIn("primitive-canvas",html)
        self.assertIn("Deze ${fmt}",html)

if __name__=="__main__":
    unittest.main()
