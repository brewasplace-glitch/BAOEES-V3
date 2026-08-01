from pathlib import Path
import ast,json,unittest

R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/structural/architectural_to_structural_model_derivation_v8_0_0.json"
P=R/"configs/projects/generic_building_structural_derivation_v8_0_0.json"
X=R/"runners/PROJECT_PHOENIX_architectural_to_structural_model_derivation_v8_0_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))

    def test_suite_identity(self):
        c=json.loads(C.read_text())
        self.assertEqual(c["suite"],"PHOENIX STRUCTURAL ENGINEERING SUITE")

    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])

    def test_candidate_only(self):
        p=json.loads(P.read_text())
        self.assertTrue(p["release"]["candidate_model_only"])
        self.assertFalse(p["release"]["professional_structural_review"])

    def test_derivation_outputs(self):
        t=X.read_text()
        for marker in (
            "structural_axis_register",
            "loadbearing_wall_candidate_register",
            "column_candidate_register",
            "beam_candidate_register",
            "slab_panel_register",
            "roof_support_candidate_register",
            "stability_zone_register",
            "structural_candidate_model"
        ):
            self.assertIn(marker,t)

    def test_traceability(self):
        t=X.read_text()
        self.assertIn("architectural_element_id",t)
        self.assertIn("architectural_space_id",t)
        self.assertIn("architectural_traceability",t)

    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_structural_approval":False',t)
        self.assertIn('"structural_model_released":False',t)

if __name__=="__main__":
    unittest.main()
