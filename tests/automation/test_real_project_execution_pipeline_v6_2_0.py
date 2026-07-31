from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/real_project_execution_pipeline_v6_2_0.json"
P=R/"configs/projects/moskee_bunschoten_real_execution_pilot_v6_2_0.json"
X=R/"runners/PROJECT_PHOENIX_real_project_execution_pipeline_v6_2_0.py"
class T(unittest.TestCase):
 def test_config(self):
  c=json.loads(C.read_text());self.assertEqual(len(c["engines"]),6);self.assertFalse(c["release"]["permit_ready"])
 def test_geometry(self):
  p=json.loads(P.read_text());s=p["scope"];self.assertEqual(s["building_extension_width_m"]*s["building_extension_length_m"]*s["storeys"],s["gross_floor_area_m2"])
 def test_anchor_blocked(self):
  p=json.loads(P.read_text());self.assertFalse(p["execution_inputs"]["site_anchor"]["permit_use_allowed"])
 def test_python(self):ast.parse(X.read_text())
 def test_engines(self):
  t=X.read_text()
  for x in ("qgis","freecad","ifcopenshell","calculix","opensees","energyplus"):self.assertIn(f'results["{x}"]',t)
 def test_gates(self):
  t=X.read_text();self.assertIn("CENTRAL DIGITAL TWIN WRITEBACK: PASSED",t);self.assertIn("PERMIT-READY RELEASE: BLOCKED",t)
if __name__=="__main__":unittest.main()
