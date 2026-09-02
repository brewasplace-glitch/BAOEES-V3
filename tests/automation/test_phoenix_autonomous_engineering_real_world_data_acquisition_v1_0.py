import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.real_world_data_acquisition import acquire_real_world_data
from phoenix.autonomy.site_parcel_intelligence import analyze_site_drawings
from phoenix.autonomy.structural_action_load_basis import build_structural_action_load_basis

class EngineeringRealWorldTests(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        (repo/"configs"/"phoenix").mkdir(parents=True)
        policy_name="structural_action_load_basis_policy_v1_0.json"
        policy_src=ROOT/"configs"/"phoenix"/policy_name
        (repo/"configs"/"phoenix"/policy_name).write_text(
            policy_src.read_text(encoding="utf-8"),encoding="utf-8"
        )
        registry_name="real_world_data_source_registry_v1_0.json"
        registry_src=ROOT/"configs"/"phoenix"/registry_name
        registry=json.loads(registry_src.read_text(encoding="utf-8"))
        registry["providers"]=[]
        (repo/"configs"/"phoenix"/registry_name).write_text(
            json.dumps(registry,indent=2)+"\n",encoding="utf-8"
        )
        return td,repo

    def context(self):
        return {"facts":{
            "country_code":"SR","region":"Paramaribo","municipality":"Paramaribo",
            "project_location":"Paramaribo, Suriname","currency":"SRD"
        }}

    def test_01_uploaded_price_and_material_catalogs_are_acquired(self):
        td,repo=self.make_repo()
        try:
            uploads=repo/"uploads";uploads.mkdir()
            price=uploads/"prices.json"
            price.write_text(json.dumps({"metadata":{"country_code":"SR"},"prices":[{"item_code":"A"}]}))
            material=uploads/"materials.json"
            material.write_text(json.dumps({"metadata":{"country_code":"SR"},"products":[{"product_id":"P"}]}))
            result=acquire_real_world_data(
                repository=repo,project_id="P1",project_context=self.context(),
                manifest={},upload_paths=[price,material]
            )
            self.assertEqual(result.register["acquired_count"],2)
            self.assertTrue((repo/"projects"/"runtime"/"P1"/"sources"/"market_prices").is_dir())
            self.assertTrue((repo/"projects"/"runtime"/"P1"/"sources"/"material_supply").is_dir())
        finally:td.cleanup()

    def test_02_no_provider_means_no_fabricated_live_data(self):
        td,repo=self.make_repo()
        try:
            result=acquire_real_world_data(
                repository=repo,project_id="P1",project_context=self.context(),
                manifest={},upload_paths=[]
            )
            self.assertEqual(result.status,"PASSED")
            self.assertEqual(result.register["acquired_count"],0)
            self.assertFalse(result.register["web_search_used"])
            self.assertTrue(result.register["only_explicit_or_configured_sources"])
        finally:td.cleanup()

    def test_03_geojson_site_boundary_yields_real_site_dimensions(self):
        td,repo=self.make_repo()
        try:
            upload=repo/"site.geojson"
            upload.write_text(json.dumps({
                "type":"Feature",
                "properties":{},
                "geometry":{"type":"Polygon","coordinates":[[
                    [-55.1700,5.8300],[-55.1698,5.8300],[-55.1698,5.8303],
                    [-55.1700,5.8303],[-55.1700,5.8300]
                ]]}
            }))
            base={"status":"SCHEMATIC_ASSUMPTION","plot":{"width_m":20,"depth_m":30}}
            result=analyze_site_drawings(
                project_id="P1",upload_paths=[upload],base_site_context=base,
                brief="",repository=repo
            )
            self.assertEqual(result.status,"PASSED")
            self.assertEqual(result.site_context["status"],"SITE_DRAWING_EVIDENCE")
            self.assertGreater(result.site_context["plot"]["width_m"],10)
            self.assertGreater(result.site_context["plot"]["depth_m"],20)
            self.assertFalse(result.site_context["cadastral_validation"])
        finally:td.cleanup()

    def test_04_dxf_requires_explicit_units(self):
        td,repo=self.make_repo()
        try:
            upload=repo/"site.dxf"
            upload.write_text("0\nSECTION\n2\nENTITIES\n0\nLWPOLYLINE\n70\n1\n10\n0\n20\n0\n10\n20\n20\n0\n10\n20\n20\n30\n10\n0\n20\n30\n0\nENDSEC\n0\nEOF\n")
            result=analyze_site_drawings(
                project_id="P1",upload_paths=[upload],
                base_site_context={"status":"SCHEMATIC_ASSUMPTION"},
                brief="",repository=repo
            )
            self.assertEqual(result.status,"NO_NEW_EVIDENCE")
            self.assertTrue(any("DXF_UNITS_REQUIRED" in x for x in result.warnings))
        finally:td.cleanup()

    def test_05_current_structural_action_load_source_passes(self):
        td,repo=self.make_repo()
        try:
            folder=repo/"inputs"/"structural_action_load";folder.mkdir(parents=True)
            source={
                "metadata":{
                    "basis_id":"SR-TEST","country_code":"SR",
                    "source_name":"TEST NORMATIVE SOURCE",
                    "effective_date":"2026-01-01","valid_until":"2099-12-31"
                },
                "action_load_input":{
                    "basis":"TEST_BASIS",
                    "unit_system":{"length":"m","force":"kN","moment":"kNm","stress":"kPa","mass":"kg"},
                    "actions":[
                        {"id":"G1","case_id":"G","case_name":"Permanent","category":"permanent",
                         "kind":"self_weight","direction":"GRAVITY","factor":1.0,
                         "target":{"all_elements":True}}
                    ],
                    "combinations":[{"id":"C1","name":"Test","terms":[{"case_id":"G","coefficient":1.0}]}]
                }
            }
            (folder/"sr.json").write_text(json.dumps(source))
            result=build_structural_action_load_basis(
                repository=repo,project_id="P1",project_context=self.context(),
                as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"PASSED")
            self.assertEqual(result.action_load_input["basis"],"TEST_BASIS")
            self.assertEqual(result.action_load_input["source_evidence"]["country_code"],"SR")
        finally:td.cleanup()

    def test_06_no_structural_source_blocks_without_fabricating_values(self):
        td,repo=self.make_repo()
        try:
            result=build_structural_action_load_basis(
                repository=repo,project_id="P1",project_context=self.context(),
                as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertEqual(result.blockers[0]["reason"],"CURRENT_STRUCTURAL_ACTION_LOAD_BASIS_REQUIRED")
        finally:td.cleanup()

    def test_07_expired_structural_source_does_not_pass(self):
        td,repo=self.make_repo()
        try:
            folder=repo/"inputs"/"structural_action_load";folder.mkdir(parents=True)
            (folder/"old.json").write_text(json.dumps({
                "metadata":{"basis_id":"OLD","country_code":"SR","source_name":"OLD","effective_date":"2020-01-01","valid_until":"2025-12-31"},
                "action_load_input":{
                    "basis":"OLD","unit_system":{"length":"m","force":"kN","moment":"kNm","stress":"kPa","mass":"kg"},
                    "actions":[{"id":"G","case_id":"G","category":"permanent","kind":"self_weight","direction":"GRAVITY","factor":1,"target":{"all_elements":True}}],
                    "combinations":[{"id":"C","terms":[{"case_id":"G","coefficient":1}]}]
                }
            }))
            result=build_structural_action_load_basis(
                repository=repo,project_id="P1",project_context=self.context(),
                as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertTrue(any(x.get("reason")=="STRUCTURAL_LOAD_SOURCE_EXPIRED" for x in result.source_register["rejections"]))
        finally:td.cleanup()

if __name__=="__main__":
    unittest.main()
