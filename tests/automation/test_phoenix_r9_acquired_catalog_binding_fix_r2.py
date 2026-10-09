from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from phoenix.autonomy import global_supplier_import_acquisition as g
from phoenix.autonomy.local_material_supply_intelligence import build_local_material_supply_context

class R9AcquiredCatalogBindingFixR2Tests(unittest.TestCase):
    def test_workspace_catalog_is_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            (repo/"configs"/"phoenix").mkdir(parents=True)
            (repo/"configs"/"phoenix"/"local_material_supply_policy_v1_0.json").write_text(json.dumps({"freshness":{"default_max_age_days":30},"remote":{"timeout_seconds":1,"maximum_bytes":10000}}),encoding="utf-8")
            (repo/"configs"/"phoenix"/"material_supply_source_registry_v1_0.json").write_text(json.dumps({"sources":[]}),encoding="utf-8")
            ws=repo/"projects"/"runtime"/"_job"/"bridge"/"workspace"
            supply=ws/"sources"/"material_supply"; supply.mkdir(parents=True)
            products=[]
            for family in ("masonry_unit","structural_concrete","reinforcement_steel","structural_timber"):
                products.append({"product_id":family+"-1","material_family":family,"engineering_material_id":family.upper()+"_ENG","technical_properties":{"declared":"TEST"},"availability_status":"IN_STOCK","availability_verified_date":"2026-10-09"})
            (supply/"catalog.json").write_text(json.dumps({"metadata":{"country_code":"SR","region_name":"Paramaribo","city":"Paramaribo","availability_verified_date":"2026-10-09","supplier_name":"TEST"},"products":products}),encoding="utf-8")
            profile={"assumptions":{"default_wall_material":"masonry_candidate","default_column_material":"reinforced_concrete_candidate","default_slab_material":"reinforced_concrete_candidate","default_beam_material":"reinforced_concrete_candidate","default_roof_material":"timber_candidate"}}
            result=build_local_material_supply_context(repository=repo,project_id="PLUTOSTRAAT",architectural_model={"building":{"type":"house"}},structural_profile=profile,project_context={"facts":{"country_code":"SR","region":"Paramaribo","municipality":"Paramaribo"}},manifest={},as_of_date="2026-10-09",workspace=ws)
            self.assertGreaterEqual(result.supply_register["catalog_count"],1)
            self.assertTrue(any(x.get("source_kind")=="project_workspace" for x in result.supply_register.get("sources",[])))

    def test_dataclass_reconciles_structured_pass(self):
        base=g.AcquisitionResult("BLOCKED",{},{"request_count":1},[],[{"reason":"STALE"}])
        def enhance(value, *, args=(), kwargs=None):
            value["status"]="PASSED"; value["blockers"]=[]; value["written_catalogs"]=["A.json"]; value["production_release"]="LOCKED"; return value
        with patch.object(g,"_phoenix_structured_evidence_original_acquire_global_supplier_import_evidence",return_value=base), patch.object(g,"_phoenix_structured_evidence_enhance",side_effect=enhance):
            result=g.acquire_global_supplier_import_evidence(repository=None,workspace=None,project_id="P",project_context={},local_selection_register={},manifest={})
        self.assertEqual(result.status,"PASSED"); self.assertEqual(result.blockers,[]); self.assertEqual(result.written_catalogs,["A.json"])

if __name__=="__main__": unittest.main()
