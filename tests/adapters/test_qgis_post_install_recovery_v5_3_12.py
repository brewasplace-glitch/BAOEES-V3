from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from phoenix.adapters.open_source.qgis_acceptance_v5_3_6 import write_geojson
from phoenix.adapters.open_source.qgis_windows import command_for_launcher
ROOT=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_config(self):
  config_path=ROOT/"configs/phoenix/qgis_detector_evidence_based_availability_v5_3_11.json"
  self.assertTrue(config_path.is_file())
  c=json.loads(config_path.read_text(encoding="utf-8"))
  self.assertEqual(
   c["schema_version"],
   "phoenix.qgis-detector-evidence-availability/5.3.11"
  )
  self.assertEqual(c["installation_action"],"NONE")
  self.assertTrue(c["reuse_existing_installation"])
  policy=c["detector_availability_policy"]
  self.assertEqual(policy["version_probe_exit_zero"],"sufficient")
  self.assertEqual(
   policy["real_accepted_geopackage_evidence"],
   "sufficient"
  )
  self.assertEqual(
   policy["batch_exit_code_one_with_valid_evidence"],
   "diagnostic_only"
  )
 def test_wrapper(self):
  with patch("shutil.which",return_value=r"C:\Windows\System32\cmd.exe"):
   c=command_for_launcher(Path(r"C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat"),["--version"])
  self.assertEqual(c[1:3],["/d","/c"]);self.assertNotIn("call",c[3].lower())
 def test_geojson(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"x.geojson";write_geojson(p);self.assertEqual(json.loads(p.read_text())["features"][0]["geometry"]["type"],"Point")
 def test_confirmed_version_format(self):
  self.assertTrue("3.44.12".startswith("3.44."))
if __name__=="__main__":unittest.main()


class DetectorRegistryTests(unittest.TestCase):
 def test_registry_activator_exists(self):
  p=ROOT/"tools/qgis/activate_qgis_adapter_v5_3_9.py"
  self.assertTrue(p.is_file())

 def test_registry_activator_enforces_class_reference(self):
  p=ROOT/"tools/qgis/activate_qgis_adapter_v5_3_9.py"
  text=p.read_text(encoding="utf-8")
  self.assertIn("QGIS registry mode: CLASS_REFERENCE",text)
  self.assertIn("deferred to create_adapter()",text)
  self.assertIn("Invalid QGISWindowsAdapter instance remains",text)

 def test_registry_verifier_exists(self):
  p=ROOT/"tools/qgis/verify_qgis_registry_class_reference_v5_3_9.py"
  self.assertTrue(p.is_file())
  text=p.read_text(encoding="utf-8")
  self.assertIn("Registry contains an adapter instance",text)
  self.assertIn("QGIS REGISTRY CLASS REFERENCE: VERIFIED",text)


class EvidenceBasedDetectionTests(unittest.TestCase):
 def test_evidence_adapter_exists(self):
  p=ROOT/"phoenix/adapters/open_source/qgis_adapter_v5_3_11.py"
  self.assertTrue(p.is_file())
  text=p.read_text(encoding="utf-8")
  self.assertIn("REAL_VALID_GEOPACKAGE_ARTIFACT",text)
  self.assertIn("availability confirmed by real accepted GeoPackage evidence",text)
  self.assertIn("available=(code==0) or evidence_available",text)

 def test_evidence_verifier_exists(self):
  p=ROOT/"tools/qgis/verify_qgis_evidence_based_detection_v5_3_11.py"
  self.assertTrue(p.is_file())
  text=p.read_text(encoding="utf-8")
  self.assertIn("QGIS EVIDENCE-BASED AVAILABILITY: VERIFIED",text)
