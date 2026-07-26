import unittest
from phoenix.commissioning_handover import CommissioningHandoverEngine

class BB28Tests(unittest.TestCase):
    def setUp(self): self.e=CommissioningHandoverEngine()
    def clean(self):
        return self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","as_built_complete":True}],
            commissioning_tests=[{"test_id":"T1","asset_id":"A1","result":"passed"}],
            handover_documents=[{"document_id":"D1","asset_id":"A1","document_type":"om_manual","status":"released"}])
    def test_clean_passes(self): self.assertTrue(self.clean()["handover_passed"])
    def test_readiness_100(self): self.assertEqual(100.0,self.clean()["handover_readiness_percent"])
    def test_missing_manual_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","as_built_complete":True}],
            commissioning_tests=[{"test_id":"T1","asset_id":"A1","result":"passed"}])
        self.assertFalse(r["handover_passed"])
    def test_failed_test_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","as_built_complete":True}],
            commissioning_tests=[{"test_id":"T1","asset_id":"A1","result":"failed"}],
            handover_documents=[{"document_id":"D1","asset_id":"A1","document_type":"om_manual","status":"released"}])
        self.assertFalse(r["handover_passed"])
    def test_critical_punch_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","as_built_complete":True}],
            commissioning_tests=[{"test_id":"T1","asset_id":"A1","result":"passed"}],
            handover_documents=[{"document_id":"D1","asset_id":"A1","document_type":"om_manual","status":"released"}],
            punch_items=[{"punch_id":"P1","severity":"critical","status":"open"}])
        self.assertFalse(r["handover_passed"])
    def test_unknown_asset_test_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","as_built_complete":True}],
            commissioning_tests=[{"test_id":"T1","asset_id":"BAD","result":"passed"}])
        self.assertFalse(r["handover_passed"])
if __name__=="__main__": unittest.main()
