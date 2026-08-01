from pathlib import Path
import ast,json,unittest

R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/asset_information_facility_management_maintenance_digital_twin_operations_v7_3_0.json"
P=R/"configs/phoenix/asset_fm_operations_project_template_v7_3_0.json"
X=R/"runners/PROJECT_PHOENIX_asset_information_facility_management_maintenance_digital_twin_operations_v7_3_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))

    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])

    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["professional_operations_acceptance"]["approved"])

    def test_registers(self):
        t=X.read_text()
        for marker in (
            "asset_register",
            "om_document_register",
            "warranty_register",
            "preventive_maintenance_register",
            "inspection_register",
            "fault_register",
            "service_history_register",
            "spare_parts_register",
            "replacement_cycle_register",
            "operations_readiness_matrix"
        ):
            self.assertIn(marker,t)

    def test_critical_spare_logic(self):
        t=X.read_text()
        self.assertIn('a["criticality"]=="CRITICAL"',t)
        self.assertIn('"critical_spares_defined"',t)

    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_operations_release":False',t)

if __name__=="__main__":
    unittest.main()
