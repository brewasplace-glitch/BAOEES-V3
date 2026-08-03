import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.local_material_supply_intelligence import (
    build_local_material_supply_context,
    derive_material_requirements,
    selected_engineering_material_ids,
)

class LocalMaterialSupplyTests(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        (repo/"configs"/"phoenix").mkdir(parents=True)
        for name in (
            "local_material_supply_policy_v1_0.json",
            "material_supply_source_registry_v1_0.json",
        ):
            src=ROOT/"configs"/"phoenix"/name
            (repo/"configs"/"phoenix"/name).write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
        return td,repo

    def profile(self):
        return {
            "assumptions":{
                "default_wall_material":"masonry_candidate",
                "default_column_material":"reinforced_concrete_candidate",
                "default_slab_material":"reinforced_concrete_candidate",
                "default_beam_material":"reinforced_concrete_candidate",
                "default_roof_material":"timber_candidate",
            }
        }

    def arch(self):
        return {"building":{"type":"detached_house"},"storeys":[]}

    def context(self,country="SR",region="Paramaribo",city="Paramaribo"):
        return {"facts":{
            "country_code":country,"region":region,"municipality":city,
            "project_location":city
        }}

    def add_catalog(self,repo,*,country="SR",region="Paramaribo",city=None,
                    verified="2026-08-01",valid_until="2026-12-31",
                    product_states=None,market_scope=None):
        folder=repo/"inputs"/"material_supply"
        folder.mkdir(parents=True,exist_ok=True)
        if product_states is None:
            product_states={
                "masonry_unit":"IN_STOCK",
                "structural_concrete":"AVAILABLE_TO_ORDER",
                "reinforcement_steel":"IN_STOCK",
                "structural_timber":"IN_STOCK",
            }
        products=[]
        for family,state in product_states.items():
            products.append({
                "product_id":"P-"+family,
                "description":"Test "+family,
                "material_family":family,
                "engineering_material_id":"ENG-"+family,
                "technical_properties":{"test_property":1},
                "availability_status":state,
                "availability_verified_date":verified,
                "availability_valid_until":valid_until,
                "unit":"unit",
                "lead_time_days":3,
            })
        metadata={
            "catalog_id":"CAT-1","supplier_id":"SUP-1","supplier_name":"TEST SUPPLIER",
            "country_code":country,"region_name":region,"source_name":"TEST SOURCE",
            "availability_verified_date":verified,
        }
        if city: metadata["city"]=city
        if market_scope: metadata["market_scope"]=market_scope
        (folder/"catalog.json").write_text(json.dumps({"metadata":metadata,"products":products}),encoding="utf-8")

    def test_01_requirements_include_concrete_rebar_masonry_timber(self):
        req=derive_material_requirements(project_id="P1",architectural_model=self.arch(),structural_profile=self.profile())
        fam={x["material_family"] for x in req["requirements"]}
        self.assertTrue({"masonry_unit","structural_concrete","reinforcement_steel","structural_timber"}.issubset(fam))

    def test_02_missing_location_blocks_local_material_confirmation(self):
        td,repo=self.make_repo()
        try:
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context={"facts":{}},manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertTrue(any(x["reason"]=="PROJECT_LOCATION_REQUIRED_FOR_LOCAL_MATERIALS" for x in result.blockers))
        finally: td.cleanup()

    def test_03_current_regional_catalog_confirms_all_required_materials(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo)
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"PASSED")
            self.assertTrue(result.selection_register["all_requirements_locally_confirmed"])
            self.assertTrue(result.selection_register["all_structural_requirements_locally_confirmed"])
            self.assertTrue(all(x["selection_status"]=="LOCAL_AVAILABILITY_CONFIRMED" for x in result.selection_register["selections"]))
        finally: td.cleanup()

    def test_04_stale_availability_does_not_count_as_confirmed(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo,verified="2025-01-01",valid_until=None)
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertFalse(result.selection_register["all_requirements_locally_confirmed"])
        finally: td.cleanup()

    def test_05_limited_stock_is_probable_not_final(self):
        td,repo=self.make_repo()
        try:
            states={
                "masonry_unit":"LIMITED_STOCK","structural_concrete":"AVAILABLE_TO_ORDER",
                "reinforcement_steel":"IN_STOCK","structural_timber":"IN_STOCK",
            }
            self.add_catalog(repo,product_states=states)
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"BLOCKED")
            masonry=next(x for x in result.selection_register["selections"] if x["material_family"]=="masonry_unit")
            self.assertEqual(masonry["selection_status"],"LOCAL_AVAILABILITY_PROBABLE")
        finally: td.cleanup()

    def test_06_foreign_catalog_is_not_silently_local(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo,country="NL",region="Zuid-Holland",market_scope="INTERNATIONAL_IMPORT")
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertTrue(any(
                x["selection_status"]=="INTERNATIONAL_IMPORT_REQUIRED"
                for x in result.selection_register["selections"]
            ))
        finally: td.cleanup()

    def test_07_structural_product_requires_engineering_id_and_properties(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo)
            path=repo/"inputs"/"material_supply"/"catalog.json"
            value=json.loads(path.read_text())
            value["products"][0].pop("technical_properties",None)
            value["products"][0].pop("engineering_material_id",None)
            path.write_text(json.dumps(value))
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertTrue(result.selection_register["all_requirements_commercially_available"])
            self.assertFalse(result.selection_register["all_structural_requirements_engineering_qualified"])
        finally: td.cleanup()

    def test_08_selected_engineering_ids_are_exposed_for_solver_gate(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo)
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            ids=selected_engineering_material_ids(result.selection_register)
            self.assertIn("ENG-structural_concrete",ids)
            self.assertIn("ENG-reinforcement_steel",ids)
        finally: td.cleanup()

    def test_09_change_control_requires_recalculation(self):
        td,repo=self.make_repo()
        try:
            self.add_catalog(repo)
            result=build_local_material_supply_context(
                repository=repo,project_id="P1",architectural_model=self.arch(),
                structural_profile=self.profile(),project_context=self.context(),manifest={},
                as_of_date="2026-08-03",
            )
            req=result.change_control["substitution_requires"]
            self.assertTrue(req["structural_recalculation_if_structural"])
            self.assertTrue(req["cost_recalculation"])
            self.assertTrue(req["qaqc_recheck"])
            self.assertFalse(result.change_control["automatic_substitution"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
