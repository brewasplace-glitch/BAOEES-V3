import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from phoenix.detv_cad_bridge import server

class TestJsonSafeRenderFailure(unittest.TestCase):
    def test_recursive_path_conversion(self):
        p=Path("C:/PROJECT-PHOENIX/example.dxf")
        safe=server.json_safe({"source":p,"nested":[{"render":p}]})
        json.dumps(safe)
        self.assertIsInstance(safe["source"],str)
        self.assertIsInstance(safe["nested"][0]["render"],str)

    def test_dual_render_failure_preserves_real_errors(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            src=td/"real-file.dxf"
            src.write_text("0\nEOF\n",encoding="ascii")
            session=td/"session"
            session.mkdir()
            with patch.object(server,"render_svg_resilient",side_effect=RuntimeError("forced SVG failure")):
                with patch.object(server,"extract_browser_primitives",side_effect=RuntimeError("forced primitive failure")):
                    result=server.process_source(src,session,{})
            self.assertEqual(result["embedded_status"],"FAILED_DXF_RENDER")
            json.dumps(server.json_safe(result))
            self.assertIsInstance(result["source"],str)
            self.assertIsInstance(result["render_source"],str)
            diag=Path(result["diagnostics_file"])
            data=json.loads(diag.read_text(encoding="utf-8"))
            self.assertEqual(data["schema"],"PHOENIX_CAD_RENDER_DIAGNOSTICS_1.1")
            dump=json.dumps(data)
            self.assertIn("forced SVG failure",dump)
            self.assertIn("forced primitive failure",dump)

if __name__=="__main__":
    unittest.main()
