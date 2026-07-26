import unittest
from phoenix.digital_twin_operations import DigitalTwinOperationsEngine

class BB29Tests(unittest.TestCase):
    def setUp(self): self.e=DigitalTwinOperationsEngine()
    def test_commissioned_passes(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":True}])
        self.assertTrue(r["operations_ready"])
    def test_uncommissioned_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":False}])
        self.assertFalse(r["operations_ready"])
    def test_lifecycle_cost(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":True}],
            maintenance_plans=[{"plan_id":"M1","asset_id":"A1","interval_days":365,"annual_cost":1000}],forecast_years=10)
        self.assertEqual(10000.0,r["lifecycle_maintenance_forecast"])
    def test_unknown_asset_plan_blocks(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":True}],
            maintenance_plans=[{"plan_id":"M1","asset_id":"BAD","interval_days":365,"annual_cost":1000}])
        self.assertFalse(r["operations_ready"])
    def test_poor_condition_warns(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":True}],
            condition_assessments=[{"assessment_id":"C1","asset_id":"A1","condition":"poor"}])
        self.assertEqual(["A1"],r["poor_condition_asset_ids"])
    def test_due_maintenance(self):
        r=self.e.create_report({"project_id":"P1"},assets=[{"asset_id":"A1","commissioned":True}],
            maintenance_plans=[{"plan_id":"M1","asset_id":"A1","interval_days":30,"annual_cost":1000}],as_of_date="2026-01-01")
        self.assertEqual(1,len(r["due_maintenance_actions"]))
if __name__=="__main__": unittest.main()
