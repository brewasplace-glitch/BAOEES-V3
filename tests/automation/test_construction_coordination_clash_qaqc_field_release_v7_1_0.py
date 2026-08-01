from pathlib import Path
import ast,json,unittest

R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/construction_coordination_clash_qaqc_field_release_v7_1_0.json"
P=R/"configs/phoenix/field_release_project_template_v7_1_0.json"
X=R/"runners/PROJECT_PHOENIX_construction_coordination_clash_qaqc_field_release_v7_1_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))

    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])

    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["professional_site_release"]["approved"])

    def test_registers(self):
        t=X.read_text()
        for marker in (
            "discipline_model_register",
            "clash_register",
            "issue_register",
            "qaqc_register",
            "work_package_register",
            "field_inspection_register",
            "field_release_matrix"
        ):
            self.assertIn(marker,t)

    def test_critical_clash_logic(self):
        t=X.read_text()
        self.assertIn('c["severity"]=="CRITICAL"',t)
        self.assertIn('"no_open_critical_clashes"',t)

    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_field_release":False',t)

if __name__=="__main__":
    unittest.main()
