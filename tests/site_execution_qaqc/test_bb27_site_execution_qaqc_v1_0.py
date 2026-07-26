import unittest
from phoenix.site_execution_qaqc import SiteExecutionQAQCEngine

class BB27Tests(unittest.TestCase):
    def setUp(self): self.e=SiteExecutionQAQCEngine()
    def test_weighted_progress(self):
        r=self.e.create_report({"project_id":"P1"},activities=[
            {"activity_id":"A1","weight":100,"progress_percent":50},
            {"activity_id":"A2","weight":300,"progress_percent":25}])
        self.assertEqual(31.25,r["weighted_progress_percent"])
    def test_clean_passes(self):
        r=self.e.create_report({"project_id":"P1"},activities=[{"activity_id":"A1","progress_percent":20}],
            inspections=[{"inspection_id":"I1","result":"passed"}])
        self.assertTrue(r["site_quality_passed"])
    def test_failed_inspection_blocks(self):
        r=self.e.create_report({"project_id":"P1"},activities=[{"activity_id":"A1","progress_percent":20}],
            inspections=[{"inspection_id":"I1","result":"failed"}])
        self.assertFalse(r["site_quality_passed"])
    def test_major_ncr_blocks(self):
        r=self.e.create_report({"project_id":"P1"},activities=[{"activity_id":"A1","progress_percent":20}],
            ncrs=[{"ncr_id":"N1","severity":"major","status":"open"}])
        self.assertFalse(r["site_quality_passed"])
    def test_closed_major_passes(self):
        r=self.e.create_report({"project_id":"P1"},activities=[{"activity_id":"A1","progress_percent":20}],
            ncrs=[{"ncr_id":"N1","severity":"major","status":"closed"}])
        self.assertTrue(r["site_quality_passed"])
    def test_invalid_progress_blocks(self):
        r=self.e.create_report({"project_id":"P1"},activities=[{"activity_id":"A1","progress_percent":120}])
        self.assertFalse(r["site_quality_passed"])
if __name__=="__main__": unittest.main()
