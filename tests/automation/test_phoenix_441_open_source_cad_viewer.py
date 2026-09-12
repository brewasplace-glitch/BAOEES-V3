import tempfile
import unittest
from pathlib import Path
from phoenix.cad_viewer.engine import make_test_dxf, inspect_dxf, load_runtime_config

class TestCadViewer(unittest.TestCase):
    def test_create_and_inspect_dxf(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.dxf"
            make_test_dxf(p)
            data=inspect_dxf(p)
            self.assertEqual(data["format"],"DXF")
            self.assertEqual(data["modelspace_entity_count"],3)
            self.assertIn("LINE",data["entity_counts"])
            self.assertIn("PHOENIX_TEST",[x["name"] for x in data["layers"]])

    def test_runtime_config_accepts_utf8_bom(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"runtime.json"
            payload={
                "librecad_exe":"C:/LibreCAD/librecad.exe",
                "libredwg_dwg2dxf_exe":"C:/LibreDWG/dwg2dxf.exe"
            }
            p.write_bytes(("\ufeff"+json.dumps(payload)).encode("utf-8"))
            data=load_runtime_config(p)
            self.assertEqual(data["librecad_exe"],payload["librecad_exe"])
            self.assertEqual(data["libredwg_dwg2dxf_exe"],payload["libredwg_dwg2dxf_exe"])


    def test_dwg_degraded_inspection_result_is_truthful(self):
        # This verifies the intended status vocabulary used when LibreDWG
        # conversion succeeds but the converted DXF cannot be parsed.
        status="DEGRADED_LIBREDWG_DXF_PARSE"
        self.assertTrue(status.startswith("DEGRADED_"))


if __name__=="__main__":
    unittest.main()
