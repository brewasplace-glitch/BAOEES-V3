from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/permit_dossier_assembly_document_control_submission_v6_9_0.json"
P=R/"configs/phoenix/permit_dossier_project_template_v6_9_0.json"
X=R/"runners/PROJECT_PHOENIX_permit_dossier_assembly_document_control_submission_v6_9_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))
    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])
    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["professional_signoff"]["approved"])
        self.assertFalse(p["submission"]["automatic_submission"])
    def test_document_control_assets(self):
        t=X.read_text()
        for m in ("document_register","revision_register","dossier_index","submission_manifest","permit_submission_package.zip"):
            self.assertIn(m,t)
    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_authority_submission":False',t)
        self.assertIn('"execution_ready":False',t)

if __name__=="__main__":
    unittest.main()
