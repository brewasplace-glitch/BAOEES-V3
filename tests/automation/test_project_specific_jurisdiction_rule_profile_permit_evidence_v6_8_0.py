from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/project_specific_jurisdiction_permit_evidence_engine_v6_8_0.json"
P=R/"configs/phoenix/rule_profiles/project_specific_jurisdiction_template_v6_8_0.json"
X=R/"runners/PROJECT_PHOENIX_project_specific_jurisdiction_rule_profile_permit_evidence_v6_8_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))
    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])
    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["jurisdiction"]["verified"])
        self.assertFalse(p["professional_review"]["approved"])
        self.assertFalse(p["submission"]["evidence_complete"])
    def test_traceability_assets(self):
        t=X.read_text()
        for marker in ("regulation_source_register","rule_traceability_register","permit_evidence_register","permit_readiness_matrix"):
            self.assertIn(marker,t)
    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_legal_approval":False',t)
        self.assertIn('"execution_ready":False',t)

if __name__=="__main__":
    unittest.main()
