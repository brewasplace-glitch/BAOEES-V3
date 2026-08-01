from pathlib import Path
import ast,json,unittest

R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/lifecycle_cost_energy_performance_condition_optimization_v7_4_0.json"
P=R/"configs/phoenix/lifecycle_optimization_project_template_v7_4_0.json"
X=R/"runners/PROJECT_PHOENIX_lifecycle_cost_energy_performance_condition_optimization_v7_4_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))

    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])

    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["financial_assumptions"]["verified"])
        self.assertFalse(p["professional_optimization_approval"]["approved"])

    def test_registers(self):
        t=X.read_text()
        for marker in (
            "lifecycle_cost_register",
            "energy_performance_register",
            "resource_performance_register",
            "performance_kpi_register",
            "performance_deviation_register",
            "condition_monitoring_register",
            "maintenance_forecast_register",
            "replacement_forecast_register",
            "optimization_recommendation_register",
            "performance_optimization_matrix"
        ):
            self.assertIn(marker,t)

    def test_lifecycle_cost_logic(self):
        t=X.read_text()
        self.assertIn("present_value_lifecycle_cost",t)
        self.assertIn("discounted(",t)

    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_optimization_action":False',t)

if __name__=="__main__":
    unittest.main()
