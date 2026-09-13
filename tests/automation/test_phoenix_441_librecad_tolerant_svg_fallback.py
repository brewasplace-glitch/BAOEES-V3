import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from phoenix.detv_cad_bridge import server

class TestLibreCadTolerantSvgFallback(unittest.TestCase):
    def test_relative_outfile_workaround_and_svg_sanitize(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            exe=td/"LibreCAD.exe"
            exe.write_bytes(b"MZ")
            src=td/"broken-but-librecad-readable.dxf"
            src.write_text("0\nEOF\n",encoding="ascii")

            captured={}
            def fake_run(cmd,**kwargs):
                captured["cmd"]=cmd
                captured["cwd"]=kwargs.get("cwd")
                self.assertEqual(cmd[1],"dxf2svg")
                self.assertEqual(cmd[2],"--outfile")
                self.assertFalse(Path(cmd[3]).is_absolute())
                out=src.parent/cmd[3]
                out.write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
                    '<script>alert(1)</script>'
                    '<line x1="0" y1="0" x2="100" y2="50" onload="x()"/>'
                    '</svg>',
                    encoding="utf-8"
                )
                return SimpleNamespace(returncode=0,stdout="ok",stderr="")

            with patch.object(server.subprocess,"run",side_effect=fake_run):
                result=server.librecad_dxf_to_svg(
                    src,td,{"librecad_exe":str(exe)}
                )

            self.assertEqual(result["renderer"],"LIBRECAD_DXF2SVG_LIBDXFRW")
            self.assertEqual(result["librecad_command_mode"],"RELATIVE_OUTFILE_BESIDE_INPUT")
            self.assertIn("<svg",result["svg"])
            self.assertNotIn("<script",result["svg"].lower())
            self.assertNotIn("onload=",result["svg"].lower())
            self.assertEqual(Path(captured["cwd"]),src.parent)

    def test_process_source_uses_librecad_after_both_ezdxf_paths_fail(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            src=td/"steel-beam-detail.dxf"
            src.write_text("0\nEOF\n",encoding="ascii")
            session=td/"session";session.mkdir()

            lc={
                "svg":'<svg xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="0" x2="1" y2="1"/></svg>',
                "layers":[],
                "read_mode":"LIBRECAD_LIBDXFRW_TOLERANT",
                "recovery_errors":[],
                "dxfversion":"",
                "renderer":"LIBRECAD_DXF2SVG_LIBDXFRW",
                "librecad_svg_file":str(session/"x.svg"),
                "librecad_svg_bytes":100,
                "librecad_stdout":"",
                "librecad_stderr":"",
                "librecad_command_mode":"RELATIVE_OUTFILE_BESIDE_INPUT",
            }

            with patch.object(server,"render_svg_resilient",side_effect=RuntimeError("missing AcDbPolyline")):
                with patch.object(server,"extract_browser_primitives",side_effect=RuntimeError("missing AcDbPolyline")):
                    with patch.object(server,"librecad_dxf_to_svg",return_value=lc):
                        result=server.process_source(src,session,{"librecad_exe":"unused"})

            self.assertEqual(result["embedded_status"],"PASS_LIBRECAD_SVG_FALLBACK")
            self.assertEqual(result["renderer"],"LIBRECAD_DXF2SVG_LIBDXFRW")
            self.assertIn("<svg",result["svg"])
            diag=json.loads(Path(result["diagnostics_file"]).read_text(encoding="utf-8"))
            self.assertIn("missing AcDbPolyline",json.dumps(diag))

if __name__=="__main__":
    unittest.main()
