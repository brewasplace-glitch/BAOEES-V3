import unittest
from phoenix.contract_administration import ContractAdministrationEngine

class BB26Tests(unittest.TestCase):
    def setUp(self): self.e=ContractAdministrationEngine()
    def clean(self):
        return self.e.create_report({"project_id":"P1"},contracts=[{"contract_id":"C1","awarded_amount":100000}],
            variations=[{"variation_id":"V1","contract_id":"C1","amount":5000,"status":"approved"}],
            payments=[{"payment_id":"P1","contract_id":"C1","certified_amount":40000}])
    def test_clean_passes(self): self.assertTrue(self.clean()["contract_control_passed"])
    def test_forecast(self): self.assertEqual(105000.0,self.clean()["forecast_final_cost"])
    def test_pending_variation(self):
        r=self.e.create_report({"project_id":"P1"},contracts=[{"contract_id":"C1","awarded_amount":100}],
            variations=[{"variation_id":"V1","contract_id":"C1","amount":20,"status":"submitted"}])
        self.assertEqual(120.0,r["forecast_final_cost"])
    def test_unknown_contract_blocks(self):
        r=self.e.create_report({"project_id":"P1"},contracts=[{"contract_id":"C1","awarded_amount":100}],
            variations=[{"variation_id":"V1","contract_id":"BAD","amount":20}])
        self.assertFalse(r["contract_control_passed"])
    def test_overpayment_blocks(self):
        r=self.e.create_report({"project_id":"P1"},contracts=[{"contract_id":"C1","awarded_amount":100}],
            payments=[{"payment_id":"P1","contract_id":"C1","certified_amount":120}])
        self.assertFalse(r["contract_control_passed"])
    def test_fingerprint_deterministic(self):
        self.assertEqual(self.clean()["report_fingerprint_sha256"],self.clean()["report_fingerprint_sha256"])
if __name__=="__main__": unittest.main()
