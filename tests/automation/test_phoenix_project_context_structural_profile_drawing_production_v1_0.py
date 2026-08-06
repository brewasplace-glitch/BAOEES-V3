import json
import pathlib
import tempfile
import unittest
import sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from phoenix.autonomy.project_context import generate_project_context
from phoenix.autonomy.structural_profile import generate_structural_project_profile
from phoenix.autonomy.drawing_production import produce_architectural_drawings
from phoenix.autonomy.architectural_bootstrap import generate_architectural_bootstrap
from phoenix.autonomy.session_adapters import run_adapter

class ProjectContextStructuralDrawingTests(unittest.TestCase):
    def model(self):
        r=generate_architectural_bootstrap(
            project_id="PHOENIX-PAT-001",project_type="BOUW",
            brief="PHOENIX-PAT-001\nOntwerp een vrijstaande woning van twee bouwlagen.",
            desired_outputs=["site_plan","floor_plans","facades","sections"],
        )
        self.assertEqual(r.status,"PASSED")
        return r

    def test_01_missing_location_is_not_invented(self):
        r=self.model()
        c=generate_project_context(project_id="PHOENIX-PAT-001",brief="Ontwerp een woning.",architectural_model=r.model)
        self.assertIsNone(c.context["facts"]["project_location"])
        self.assertIsNone(c.context["facts"]["country_code"])
        self.assertIsNone(c.context["facts"]["currency"])
        self.assertEqual(c.site_context["status"],"SCHEMATIC_ASSUMPTION")
        self.assertFalse(c.site_context["plot"]["legal_boundary"])

    def test_02_explicit_nl_location_derives_eur(self):
        r=self.model()
        c=generate_project_context(
            project_id="PHOENIX-PAT-001",
            brief="Locatie: Amsterdam, Nederland\nPerceel 20 x 30 m\nOntwerp een woning.",
            architectural_model=r.model,
        )
        self.assertEqual(c.context["facts"]["project_location"],"Amsterdam, Nederland")
        self.assertEqual(c.context["facts"]["country_code"],"NL")
        self.assertEqual(c.context["facts"]["currency"],"EUR")
        self.assertEqual(c.site_context["status"],"PROJECT_INPUT_CANDIDATE")

    def test_03_structural_profile_has_v8_required_assumptions_without_load_fabrication(self):
        r=self.model()
        c=generate_project_context(project_id="PHOENIX-PAT-001",brief="Ontwerp een woning.",architectural_model=r.model)
        p=generate_structural_project_profile(project_id="PHOENIX-PAT-001",architectural_model=r.model,project_context=c.context)
        required={
            "minimum_loadbearing_wall_thickness_m","default_wall_material",
            "column_grid_target_m","default_column_material","default_slab_material",
            "maximum_preferred_slab_span_m","default_beam_material","default_roof_material",
        }
        self.assertTrue(required.issubset(p["assumptions"]))
        self.assertEqual(p["loads"]["status"],"NOT_DEFINED_BY_THIS_GENERATOR")
        self.assertIsNone(p["code_basis"]["standard"])
        self.assertFalse(p["automatic_structural_approval"])
        self.assertEqual(p["production_release"],"LOCKED")

    def test_04_bootstrap_walls_are_v8_compatible(self):
        r=self.model()
        wall=r.detailed_elements["storeys"][0]["walls"][0]
        for key in ("element_id","storey_id","category","length_m","height_m","thickness_m"):
            self.assertIn(key,wall)
        self.assertGreater(wall["length_m"],0)

    def test_05_drawing_engine_produces_floor_facade_section_svg_dxf(self):
        r=self.model()
        c=generate_project_context(project_id="PHOENIX-PAT-001",brief="Ontwerp een woning.",architectural_model=r.model)
        with tempfile.TemporaryDirectory() as td:
            result=produce_architectural_drawings(
                project_id="PHOENIX-PAT-001",architectural_model=r.model,
                site_context=c.site_context,output_dir=pathlib.Path(td),
                requested_outputs=["floor_plans","facades","sections"],
            )
            self.assertEqual(result["coverage"]["floor_plans"]["status"],"PASSED")
            self.assertEqual(result["coverage"]["facades"]["status"],"PASSED")
            self.assertEqual(result["coverage"]["sections"]["status"],"PASSED")
            self.assertTrue(any(p.suffix==".svg" for p in result["files"]))
            self.assertTrue(any(p.suffix==".dxf" for p in result["files"]))

    def test_06_schematic_site_plan_does_not_false_pass(self):
        r=self.model()
        c=generate_project_context(project_id="PHOENIX-PAT-001",brief="Ontwerp een woning.",architectural_model=r.model)
        with tempfile.TemporaryDirectory() as td:
            result=produce_architectural_drawings(
                project_id="PHOENIX-PAT-001",architectural_model=r.model,
                site_context=c.site_context,output_dir=pathlib.Path(td),
                requested_outputs=["site_plan"],
            )
            self.assertEqual(result["coverage"]["site_plan"]["status"],"BLOCKED")
            self.assertEqual(result["coverage"]["site_plan"]["reason"],"SITE_FACTS_REQUIRED_FOR_SITUATION_PLAN")
            self.assertTrue((pathlib.Path(td)/"site_plan.svg").is_file())

    def test_07_explicit_plot_allows_candidate_site_plan_output(self):
        r=self.model()
        c=generate_project_context(
            project_id="PHOENIX-PAT-001",
            brief="Locatie: Amsterdam, Nederland\nPerceel 20 x 30 m",
            architectural_model=r.model,
        )
        with tempfile.TemporaryDirectory() as td:
            result=produce_architectural_drawings(
                project_id="PHOENIX-PAT-001",architectural_model=r.model,
                site_context=c.site_context,output_dir=pathlib.Path(td),
                requested_outputs=["site_plan"],
            )
            self.assertEqual(result["coverage"]["site_plan"]["status"],"PASSED")
            self.assertFalse(c.site_context["plot"]["legal_boundary"])

    def make_repo(self,brief):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        for rel in [
            "projects/runtime/PHOENIX-PAT-001/inputs","projects/runtime/PHOENIX-PAT-001/digital_twin",
            "projects/runtime/PHOENIX-PAT-001/orchestration","projects/runtime/PHOENIX-PAT-001/results",
            "projects/runtime/PHOENIX-PAT-001/logs","outputs/runtime/phoenix_start_v3_sessions",
            "inputs/runtime/official_start_v3_uploads","configs/phoenix",
        ]:(repo/rel).mkdir(parents=True,exist_ok=True)
        session={
            "session_id":"PHX-CTX-TEST","project_type":"BOUW","project_mode":"autonomous",
            "brief":brief,"selected_project":None,"upload_batch":None,
            "desired_outputs":["site_plan","floor_plans","facades","sections","cost_estimate","permit_dossier"],
            "bootstrap":{
                "project_id":"PHOENIX-PAT-001","workspace":"projects/runtime/PHOENIX-PAT-001",
                "project_manifest":"projects/runtime/PHOENIX-PAT-001/project_manifest.json",
                "digital_twin_state":"projects/runtime/PHOENIX-PAT-001/digital_twin/project_state.json",
                "orchestration_plan":"projects/runtime/PHOENIX-PAT-001/orchestration/dependency_plan.json",
            },
        }
        sf=repo/"outputs/runtime/phoenix_start_v3_sessions/PHX-CTX-TEST.json"
        sf.write_text(json.dumps(session),encoding="utf-8")
        manifest=repo/"projects/runtime/PHOENIX-PAT-001/project_manifest.json"
        manifest.write_text(json.dumps({"project_id":"PHOENIX-PAT-001"}),encoding="utf-8")
        return td,repo,session,sf

    def test_08_architecture_adapter_writes_context_profile_drawings_and_manifest(self):
        td,repo,session,sf=self.make_repo("Locatie: Amsterdam, Nederland\nPerceel 20 x 30 m\nOntwerp een vrijstaande woning van twee bouwlagen.")
        try:
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results/session_adapters/architecture"
            rc=run_adapter("architecture",repo,sf,ws,out)
            self.assertEqual(rc,0)
            result=json.loads((out/"adapter_result.json").read_text())
            self.assertEqual(result["metadata"]["desired_output_states"]["floor_plans"]["status"],"PASSED")
            self.assertEqual(result["metadata"]["desired_output_states"]["site_plan"]["status"],"PASSED")
            self.assertTrue((out/"structural_project_profile.json").is_file())
            self.assertTrue((out/"project_context.json").is_file())
            self.assertTrue((out/"architectural_drawing_register.json").is_file())
            m=json.loads((ws/"project_manifest.json").read_text())
            self.assertEqual(m["currency"],"EUR")
            self.assertEqual(m["location"],"Amsterdam, Nederland")
        finally:td.cleanup()

    def test_09_permit_and_cost_consume_context_and_cost_continues_with_unresolved_price_evidence(self):
        td,repo,session,sf=self.make_repo("Locatie: Amsterdam, Nederland\nPerceel 20 x 30 m\nOntwerp een vrijstaande woning van twee bouwlagen.\n[PHOENIX_MATERIAL_CERTIFICATION_MODE=UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED]")
        try:
            # The temporary repository must use the installed Local Cost Intelligence
            # source/policy contracts, just like the real repository.
            for name in (
                "local_cost_intelligence_policy_v1_0.json",
                "currency_jurisdiction_catalog_v1_0.json",
                "market_price_source_registry_v1_0.json",
            ):
                (repo/"configs/phoenix"/name).write_text(
                    (ROOT/"configs/phoenix"/name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

            ws=repo/session["bootstrap"]["workspace"]
            arch_out=ws/"results/session_adapters/architecture"
            self.assertEqual(run_adapter("architecture",repo,sf,ws,arch_out),0)
            arch_result=json.loads((arch_out/"adapter_result.json").read_text())
            (ws/"orchestration/adapter_state.json").write_text(json.dumps({
                "capabilities":{"architecture":{
                    "status":"PASSED","outputs":arch_result["outputs"],"metadata":arch_result["metadata"]
                }}
            }),encoding="utf-8")

            self.assertEqual(run_adapter("permit",repo,sf,ws,ws/"results/session_adapters/permit"),0)

            # Explicit geography correctly derives EUR. Missing current local price evidence
            # is now an auditable unresolved cost input, not an adapter blocker. Phoenix must
            # continue without inventing a price.
            cost_out=ws/"results/session_adapters/cost_planning"
            self.assertEqual(run_adapter("cost_planning",repo,sf,ws,cost_out),0)
            unresolved=json.loads((cost_out/"adapter_result.json").read_text())
            self.assertEqual(unresolved["status"],"PASSED")
            cost_input=json.loads((cost_out/"cost_planning_input_register.json").read_text())
            self.assertEqual(cost_input["price_evidence_status"],"UNRESOLVED")
            self.assertFalse(cost_input.get("price_fabricated",True))

            # Add a valid current NL/EUR test ratebook with explicit evidence.
            market_dir=repo/"inputs"/"market_prices"
            market_dir.mkdir(parents=True,exist_ok=True)
            ratebook={
                "metadata":{
                    "ratebook_id":"TEST-NL-CURRENT",
                    "title":"Current NL test pricebook",
                    "country_code":"NL",
                    "currency":"EUR",
                    "effective_date":"2026-01-01",
                    "valid_until":"2099-12-31",
                    "source_name":"TEST LOCAL PRICE SOURCE",
                    "confidence":"HIGH",
                    "taxes_included":False
                },
                "prices":[{
                    "item_code":"TEST-001",
                    "description":"Test local construction item",
                    "unit":"st",
                    "unit_price":100.0
                }]
            }
            (market_dir/"nl_current_test_ratebook.json").write_text(
                json.dumps(ratebook),encoding="utf-8"
            )

            # Current price evidence is now available. Material availability is independent:
            # unknown/unavailable supply may remain unresolved, but Cost Planning continues and
            # must not fabricate supply or price data.
            self.assertEqual(run_adapter("cost_planning",repo,sf,ws,cost_out),0)
            price_confirmed=json.loads((cost_out/"adapter_result.json").read_text())
            self.assertEqual(price_confirmed["status"],"PASSED")
            cost_input=json.loads((cost_out/"cost_planning_input_register.json").read_text())
            self.assertEqual(cost_input["price_evidence_status"],"CONFIRMED")
            self.assertFalse(any(
                item.get("reason")=="LOCAL_MATERIAL_AVAILABILITY_REQUIRED_FOR_COST_PLAN"
                for item in price_confirmed.get("blockers",[])
            ))

            # Install the same material/supply source contracts in the temporary
            # repository and add a current Amsterdam/NL supplier catalog that
            # covers the material families generated by the autonomous house
            # structural profile.
            for name in (
                "local_material_supply_policy_v1_0.json",
                "material_supply_source_registry_v1_0.json",
            ):
                (repo/"configs/phoenix"/name).write_text(
                    (ROOT/"configs/phoenix"/name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

            supply_dir=repo/"inputs"/"material_supply"
            supply_dir.mkdir(parents=True,exist_ok=True)
            supplier_catalog={
                "metadata":{
                    "catalog_id":"TEST-NL-AMSTERDAM-CURRENT",
                    "supplier_id":"TEST-SUPPLIER-NL",
                    "supplier_name":"TEST LOCAL SUPPLIER",
                    "country_code":"NL",
                    "region_name":"Noord-Holland",
                    "city":"Amsterdam",
                    "currency":"EUR",
                    "source_name":"TEST LOCAL SUPPLY SOURCE",
                    "confidence":"HIGH",
                    "availability_verified_date":"2026-08-01",
                    "availability_valid_until":"2099-12-31"
                },
                "products":[
                    {
                        "product_id":"TEST-MASONRY",
                        "description":"Test local masonry product",
                        "material_family":"masonry_unit",
                        "engineering_material_id":"TEST-MASONRY-ENG",
                        "technical_properties":{"compressive_strength_mpa":10.0},
                        "availability_status":"IN_STOCK",
                        "availability_verified_date":"2026-08-01",
                        "availability_valid_until":"2099-12-31",
                        "unit":"st"
                    },
                    {
                        "product_id":"TEST-CONCRETE",
                        "description":"Test local structural concrete",
                        "material_family":"structural_concrete",
                        "engineering_material_id":"TEST-CONCRETE-ENG",
                        "technical_properties":{"compressive_strength_mpa":30.0},
                        "availability_status":"AVAILABLE_TO_ORDER",
                        "availability_verified_date":"2026-08-01",
                        "availability_valid_until":"2099-12-31",
                        "unit":"m3"
                    },
                    {
                        "product_id":"TEST-REBAR",
                        "description":"Test local reinforcement steel",
                        "material_family":"reinforcement_steel",
                        "engineering_material_id":"TEST-REBAR-ENG",
                        "technical_properties":{"yield_strength_mpa":500.0},
                        "availability_status":"IN_STOCK",
                        "availability_verified_date":"2026-08-01",
                        "availability_valid_until":"2099-12-31",
                        "unit":"kg"
                    },
                    {
                        "product_id":"TEST-TIMBER",
                        "description":"Test local structural timber",
                        "material_family":"structural_timber",
                        "engineering_material_id":"TEST-TIMBER-ENG",
                        "technical_properties":{"strength_class":"TEST"},
                        "availability_status":"IN_STOCK",
                        "availability_verified_date":"2026-08-01",
                        "availability_valid_until":"2099-12-31",
                        "unit":"m3"
                    }
                ]
            }
            (supply_dir/"amsterdam_current_material_supply.json").write_text(
                json.dumps(supplier_catalog),encoding="utf-8"
            )

            # Re-run architecture so its Local Material Supply register is built
            # from the newly available supplier evidence, then refresh adapter state.
            self.assertEqual(run_adapter("architecture",repo,sf,ws,arch_out),0)
            arch_result=json.loads((arch_out/"adapter_result.json").read_text())
            (ws/"orchestration/adapter_state.json").write_text(json.dumps({
                "capabilities":{"architecture":{
                    "status":"PASSED","outputs":arch_result["outputs"],"metadata":arch_result["metadata"]
                }}
            }),encoding="utf-8")

            self.assertEqual(run_adapter("cost_planning",repo,sf,ws,cost_out),0)
            passed=json.loads((cost_out/"adapter_result.json").read_text())
            self.assertEqual(passed["status"],"PASSED")
            self.assertEqual(passed["metadata"]["project_currency"],"EUR")
            self.assertFalse(passed["metadata"]["fx_used"])
        finally:td.cleanup()

if __name__=="__main__":unittest.main()
