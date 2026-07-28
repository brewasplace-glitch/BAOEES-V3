from pathlib import Path
import json, tempfile, unittest
from unittest.mock import patch
from phoenix.adapters.open_source.engines import create_adapter, ADAPTERS
from phoenix.adapters.open_source.registry import detect_all

class Tests(unittest.TestCase):
    def test_registry_has_six_engines(self):
        self.assertEqual(set(ADAPTERS), {"ifcopenshell","freecad","energyplus","opensees","calculix","qgis"})

    def test_detection_never_claims_missing_engine(self):
        with patch("shutil.which", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                report=detect_all()
                self.assertTrue(all(not x["available"] for x in report["engines"].values()))

    def test_commands(self):
        jobs={
          "ifcopenshell":{"input_path":"a.ifc","output_dir":"out","output_name":"a.glb"},
          "freecad":{"input_path":"a.py","output_dir":"out"},
          "energyplus":{"input_path":"a.idf","output_dir":"out"},
          "opensees":{"input_path":"a.tcl","output_dir":"out"},
          "calculix":{"input_path":"a.inp","output_dir":"out"},
          "qgis":{"input_path":"a.json","output_dir":"out","algorithm":"native:buffer","parameters":{"DISTANCE":10}}
        }
        for engine,job in jobs.items():
            cmd=create_adapter(engine).build_command(job,engine)
            self.assertEqual(cmd[0],engine)
            self.assertGreater(len(cmd),1)

    def test_missing_input_is_rejected(self):
        errors=create_adapter("energyplus").validate_job({"input_path":"missing.idf","output_dir":"out"})
        self.assertTrue(errors)

if __name__=="__main__":
    unittest.main()
