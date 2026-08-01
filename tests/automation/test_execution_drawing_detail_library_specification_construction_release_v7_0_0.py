from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/execution_drawing_detail_library_specification_release_v7_0_0.json"
P=R/"configs/phoenix/execution_release_project_template_v7_0_0.json"
L=R/"configs/phoenix/detail_library/architectural_detail_library_v7_0_0.json"
X=R/"runners/PROJECT_PHOENIX_execution_drawing_detail_library_specification_construction_release_v7_0_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))
    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])
    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["professional_release"]["approved"])
    def test_detail_library(self):
        lib=json.loads(L.read_text())
        self.assertGreaterEqual(len(lib["details"]),5)
    def test_registers(self):
        t=X.read_text()
        for m in ("detail_register","execution_document_register","material_specification_register","product_requirement_register","constructability_check_register","execution_release_matrix"):
            self.assertIn(m,t)
    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_construction_release":False',t)

if __name__=="__main__":
    unittest.main()
