from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/architectural_compliance_fire_accessibility_building_physics_v6_7_0.json"
P=R/"configs/phoenix/rule_profiles/generic_unverified_architectural_rules_v6_7_0.json"
X=R/"runners/PROJECT_PHOENIX_architectural_compliance_fire_accessibility_building_physics_v6_7_0.py"
class T(unittest.TestCase):
 def test_generic(self):
  c=json.loads(C.read_text());self.assertFalse(c["dependency"]["pilot_project_dependency"])
 def test_profile_unverified(self):
  p=json.loads(P.read_text());self.assertFalse(p["jurisdiction"]["verified"]);self.assertFalse(p["legal_release"]["professional_approval"])
 def test_python(self):ast.parse(X.read_text())
 def test_domains(self):
  t=X.read_text()
  for m in ("fire_compartments","escape_routes","accessibility","daylight","ventilation","thermal_envelope","moisture_risk"):self.assertIn(m,t)
 def test_release_safety(self):
  t=X.read_text();self.assertIn("automatic_legal_approval",t);self.assertIn("jurisdiction_profile_verified",t)
if __name__=="__main__":unittest.main()
