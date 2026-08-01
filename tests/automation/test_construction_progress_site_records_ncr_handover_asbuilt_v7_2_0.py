from pathlib import Path
import ast,json,unittest

R=Path(__file__).resolve().parents[2]
C=R/"configs/phoenix/construction_progress_site_records_ncr_handover_asbuilt_v7_2_0.json"
P=R/"configs/phoenix/construction_handover_project_template_v7_2_0.json"
X=R/"runners/PROJECT_PHOENIX_construction_progress_site_records_ncr_handover_asbuilt_v7_2_0.py"

class T(unittest.TestCase):
    def test_python(self):
        ast.parse(X.read_text(encoding="utf-8"))

    def test_no_pilot_dependency(self):
        self.assertFalse(json.loads(C.read_text())["pilot_project_dependency"])

    def test_template_locked(self):
        p=json.loads(P.read_text())
        self.assertFalse(p["professional_completion_release"]["approved"])

    def test_registers(self):
        t=X.read_text()
        for marker in (
            "progress_register",
            "daily_site_record_register",
            "site_evidence_register",
            "ncr_register",
            "change_deviation_register",
            "punch_list_register",
            "commissioning_register",
            "as_built_document_register",
            "handover_document_register",
            "completion_handover_matrix"
        ):
            self.assertIn(marker,t)

    def test_critical_ncr_logic(self):
        t=X.read_text()
        self.assertIn('n["severity"]=="CRITICAL"',t)
        self.assertIn('"no_open_critical_ncrs"',t)

    def test_release_safety(self):
        t=X.read_text()
        self.assertIn('"automatic_handover_release":False',t)

if __name__=="__main__":
    unittest.main()
