from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2];C=R/"configs/phoenix/professional_evidence_closure_engine_v6_3_0.json";X=R/"runners/PROJECT_PHOENIX_professional_evidence_closure_engine_v6_3_0.py"
class T(unittest.TestCase):
 def test_six(self):self.assertEqual(len(json.loads(C.read_text())["requirements"]),6)
 def test_no_auto(self):self.assertTrue(json.loads(C.read_text())["closure_policy"]["automatic_professional_approval_forbidden"])
 def test_python(self):ast.parse(X.read_text())
 def test_req108(self):self.assertIn("REQ-108",X.read_text())
 def test_gate(self):self.assertIn("permit_ready_release_gate.json",X.read_text())
if __name__=="__main__":unittest.main()
