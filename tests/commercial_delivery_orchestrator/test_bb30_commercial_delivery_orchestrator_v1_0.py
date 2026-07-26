import tempfile, unittest, zipfile
from phoenix.commercial_delivery_orchestrator import CommercialDeliveryExporter, CommercialDeliveryOrchestrator

def upstream(project_id="P1"):
    names=["building_model","architectural_drawings","structural_design","quantity_takeoff","cost_estimation",
           "bim_coordination","construction_documentation","construction_planning","procurement_tendering",
           "contract_administration","site_qaqc","commissioning_handover","digital_twin_operations"]
    return {name:{"project_id":project_id,"blocking_issue_count":0,"passed":True} for name in names}

def deliverables():
    types=["3d_impression","structural_calculations","structural_report","building_drawings",
           "technical_specification","specification_drawings","cost_calculation","material_schedules","site_plan"]
    return [{"deliverable_id":f"D-{i:02d}","deliverable_type":t,"status":"released","revision":"P01",
             "file_name":f"{t}.pdf","sha256":"a"*64} for i,t in enumerate(types,1)]

class BB30Tests(unittest.TestCase):
    def setUp(self):
        self.e=CommercialDeliveryOrchestrator(); self.x=CommercialDeliveryExporter()
    def test_complete_ready(self):
        m=self.e.create_delivery_manifest({"project_id":"P1","project_name":"Pilot"},upstream_reports=upstream(),deliverables=deliverables())
        self.assertTrue(m["commercial_package_ready"])
    def test_release_status(self):
        m=self.e.create_delivery_manifest({"project_id":"P1"},upstream_reports=upstream(),deliverables=deliverables(),release_requested=True)
        self.assertEqual("released_for_commercial_pilot",m["release_status"])
    def test_missing_deliverable_blocks(self):
        m=self.e.create_delivery_manifest({"project_id":"P1"},upstream_reports=upstream(),deliverables=deliverables()[:-1])
        self.assertFalse(m["commercial_package_ready"])
    def test_invalid_hash_blocks(self):
        values=deliverables(); values[0]["sha256"]="bad"
        m=self.e.create_delivery_manifest({"project_id":"P1"},upstream_reports=upstream(),deliverables=values)
        self.assertFalse(m["commercial_package_ready"])
    def test_project_mismatch_blocks(self):
        values=upstream(); values["building_model"]["project_id"]="OTHER"
        m=self.e.create_delivery_manifest({"project_id":"P1"},upstream_reports=values,deliverables=deliverables())
        self.assertFalse(m["commercial_package_ready"])
    def test_exports(self):
        m=self.e.create_delivery_manifest({"project_id":"P1","project_name":"Pilot"},upstream_reports=upstream(),deliverables=deliverables(),release_requested=True)
        with tempfile.TemporaryDirectory() as tmp:
            paths=self.x.export_all(m,tmp)
            self.assertEqual(5,len(paths)); self.assertTrue(all(p.is_file() for p in paths.values()))
            with zipfile.ZipFile(paths["dossier"]) as z: names=set(z.namelist())
            self.assertIn("commercial_building_delivery_manifest.json",names)
if __name__=="__main__": unittest.main()
