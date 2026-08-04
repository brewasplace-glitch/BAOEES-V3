import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.suriname_structural_load_basis import ensure_suriname_structural_load_basis
from phoenix.autonomy.structural_action_load_basis import build_structural_action_load_basis
from phoenix.autonomy.local_product_qualification import prepare_local_product_qualification_overlay
from phoenix.autonomy.desired_output_evidence import validate_desired_output_evidence
from phoenix.autonomy.local_material_supply_intelligence import build_local_material_supply_context
from phoenix.autonomy.deliverable_evidence_resolver import build_minimum_deliverable_manifest


class MasterpackTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        repo = pathlib.Path(td.name)
        (repo / "configs" / "phoenix").mkdir(parents=True)
        for name in (
            "building_minimum_deliverable_baseline_v1_0.json",
            "suriname_structural_knowledge_policy_v1_0.json",
        ):
            src = ROOT / "configs" / "phoenix" / name
            (repo / "configs" / "phoenix" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        return td, repo

    def ctx(self, repo, workspace, output):
        return {
            "repository": repo,
            "workspace": workspace,
            "output_dir": output,
            "project_id": "P1",
            "session": {
                "project_id": "P1",
                "project_type": "BOUW",
                "project_mode": "autonomous",
                "brief": "Ontwerp een vrijstaande woning van twee bouwlagen in Paramaribo, Suriname.",
                "desired_outputs": ["floor_plans", "facades", "sections", "site_plan"],
            },
        }

    def write_context(self, repo, workspace):
        p = workspace / "results" / "session_adapters" / "architecture" / "project_context.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"facts": {"country_code": "SR", "region": "Paramaribo", "municipality": "Paramaribo", "currency": "SRD"}}), encoding="utf-8")
        return p.relative_to(repo).as_posix()

    def test_01_suriname_load_basis_is_project_scoped_and_excludes_snow(self):
        td, repo = self.make_repo()
        try:
            ws = repo / "projects" / "runtime" / "P1"
            out = ws / "results" / "session_adapters" / "structural_engineering"
            ref = self.write_context(repo, ws)
            result = ensure_suriname_structural_load_basis(self.ctx(repo, ws, out), project_context_ref=ref)
            self.assertEqual(result["status"], "PASSED")
            source = json.loads((repo / result["source"]).read_text(encoding="utf-8"))
            action = source["action_load_input"]
            self.assertFalse(action["snow_action"]["included"])
            self.assertTrue(any(x["kind"] == "self_weight" for x in action["actions"]))
            self.assertTrue(any(x.get("magnitude") == -1.75 for x in action["actions"]))
            self.assertTrue(any(abs(x.get("magnitude", 0)) == 0.45 for x in action["actions"]))
            self.assertTrue(any(t["coefficient"] == 1.20 for c in action["combinations"] for t in c["terms"]))
            self.assertTrue(any(t["coefficient"] == 1.50 for c in action["combinations"] for t in c["terms"]))
            self.assertFalse(source["metadata"]["verified_as_current_law"])
            selected = build_structural_action_load_basis(
                repository=repo, project_id="P1",
                project_context={"facts": {"country_code": "SR", "region": "Paramaribo", "municipality": "Paramaribo"}},
            )
            self.assertEqual(selected.status, "PASSED")
            self.assertEqual(selected.action_load_input["basis"], action["basis"])
        finally:
            td.cleanup()

    def test_02_non_suriname_load_basis_is_not_applicable(self):
        td, repo = self.make_repo()
        try:
            ws = repo / "projects" / "runtime" / "P1"
            out = ws / "results" / "session_adapters" / "structural_engineering"
            p = ws / "results" / "session_adapters" / "architecture" / "project_context.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"facts": {"country_code": "NL"}}), encoding="utf-8")
            result = ensure_suriname_structural_load_basis(self.ctx(repo, ws, out), project_context_ref=p.relative_to(repo).as_posix())
            self.assertEqual(result["status"], "NOT_APPLICABLE")
            self.assertIsNone(result["source"])
        finally:
            td.cleanup()

    def test_03_local_product_overlay_only_qualifies_explicit_grades(self):
        td, repo = self.make_repo()
        try:
            ws = repo / "projects" / "runtime" / "P1"
            out = ws / "results" / "session_adapters" / "architecture"
            source_dir = ws / "sources" / "material_supply"
            source_dir.mkdir(parents=True)
            (source_dir / "supplier.json").write_text(json.dumps({
                "metadata": {"country_code": "SR", "region_name": "Paramaribo", "city": "Paramaribo", "currency": "SRD", "source_name": "TEST"},
                "products": [
                    {"product_id": "C30", "description": "Ready mix concrete C30/37", "availability_status": "AVAILABLE_TO_ORDER", "technical_properties": {"declared": "C30/37"}},
                    {"product_id": "R", "description": "Beton ijzer B500B 12 mm", "availability_status": "IN_STOCK", "technical_properties": {"diameter_mm": 12}},
                    {"product_id": "CRANGE", "description": "Ready mix concrete C8/10-C53/65", "availability_status": "AVAILABLE_TO_ORDER", "technical_properties": {"declared_grade_range": "C8/10-C53/65"}},
                ]
            }), encoding="utf-8")
            result = prepare_local_product_qualification_overlay(
                self.ctx(repo, ws, out),
                project_context={"facts": {"country_code": "SR", "region": "Paramaribo", "municipality": "Paramaribo", "currency": "SRD"}},
            )
            overlay = json.loads((repo / result["overlay"]).read_text(encoding="utf-8"))
            by_id = {x["product_id"]: x for x in overlay["products"]}
            self.assertEqual(by_id["C30"]["engineering_material_id"], "CONCRETE_C30_37")
            self.assertEqual(by_id["R"]["engineering_material_id"], "REINFORCEMENT_B500B")
            self.assertIsNone(by_id["CRANGE"].get("engineering_material_id"))
            self.assertEqual(by_id["C30"]["availability_status"], "AVAILABLE_TO_ORDER")
        finally:
            td.cleanup()


    def test_03b_qualified_overlay_can_satisfy_existing_material_gate_when_evidence_is_complete(self):
        td, repo = self.make_repo()
        try:
            # Existing material engine policy/registry are part of the installed Phoenix repo.
            for name in ("local_material_supply_policy_v1_0.json", "material_supply_source_registry_v1_0.json"):
                src = ROOT / "configs" / "phoenix" / name
                (repo / "configs" / "phoenix" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            ws = repo / "projects" / "runtime" / "P1"
            out = ws / "results" / "session_adapters" / "architecture"
            source_dir = ws / "sources" / "material_supply"
            source_dir.mkdir(parents=True)
            products = [
                {"product_id":"M","description":"VABI masonry block 10 MPa","material_family":"masonry_unit","availability_status":"IN_STOCK","availability_verified_date":"2026-08-04","engineering_material_id":"MASONRY_UNIT_FK_10","technical_properties":{"declared_compressive_strength_mpa":10}},
                {"product_id":"C","description":"Ready mix concrete C30/37","material_family":"structural_concrete","availability_status":"AVAILABLE_TO_ORDER","availability_verified_date":"2026-08-04","engineering_material_id":"CONCRETE_C30_37","technical_properties":{"declared_concrete_strength_class":"C30/37"}},
                {"product_id":"R","description":"Beton ijzer B500B","material_family":"reinforcement_steel","availability_status":"IN_STOCK","availability_verified_date":"2026-08-04","engineering_material_id":"REINFORCEMENT_B500B","technical_properties":{"declared_reinforcement_grade":"B500B"}},
                {"product_id":"T","description":"Structural timber C24","material_family":"structural_timber","availability_status":"AVAILABLE_TO_ORDER","availability_verified_date":"2026-08-04","engineering_material_id":"TIMBER_C24","technical_properties":{"declared_timber_strength_class":"C24"}},
            ]
            (source_dir / "complete.json").write_text(json.dumps({"metadata":{"country_code":"SR","region_name":"Paramaribo","city":"Paramaribo","currency":"SRD","source_name":"TEST","availability_verified_date":"2026-08-04"},"products":products}), encoding="utf-8")
            profile={"assumptions":{"default_wall_material":"masonry_candidate","default_column_material":"reinforced_concrete_candidate","default_slab_material":"reinforced_concrete_candidate","default_beam_material":"reinforced_concrete_candidate","default_roof_material":"timber_candidate"}}
            result=build_local_material_supply_context(repository=repo,project_id="P1",architectural_model={"building":{"type":"house"}},structural_profile=profile,project_context={"facts":{"country_code":"SR","region":"Paramaribo","municipality":"Paramaribo","currency":"SRD"}},manifest={},as_of_date="2026-08-04")
            self.assertTrue(result.selection_register["all_requirements_locally_confirmed"])
            self.assertTrue(result.selection_register["all_structural_requirements_engineering_qualified"])
        finally:
            td.cleanup()

    def test_04_desired_output_guard_requires_real_viewer_and_video(self):
        td, repo = self.make_repo()
        try:
            ws = repo / "projects" / "runtime" / "P1"
            d = ws / "results" / "session_adapters" / "architecture" / "drawings"
            d.mkdir(parents=True)
            (d / "floor_plan_L0.svg").write_text("<svg/>", encoding="utf-8")
            caps = {"architecture": {"outputs": [(d / "floor_plan_L0.svg").relative_to(repo).as_posix()]}, "digital_twin": {"outputs": []}}
            floor = validate_desired_output_evidence(repository=repo, workspace=ws, output_id="floor_plans", capability_states=caps)
            viewer = validate_desired_output_evidence(repository=repo, workspace=ws, output_id="viewer_3d", capability_states=caps)
            video = validate_desired_output_evidence(repository=repo, workspace=ws, output_id="auto_video", capability_states=caps)
            self.assertEqual(floor["status"], "PASSED")
            self.assertEqual(viewer["status"], "BLOCKED")
            self.assertEqual(video["status"], "BLOCKED")
        finally:
            td.cleanup()

    def test_05_deliverable_resolver_maps_existing_architecture_artifacts(self):
        td, repo = self.make_repo()
        try:
            ws = repo / "projects" / "runtime" / "P1"
            arch = ws / "results" / "session_adapters" / "architecture"
            drawings = arch / "drawings"
            drawings.mkdir(parents=True)
            paths = []
            for name in [
                "floor_plan_L0.svg", "floor_plan_L1.svg",
                "elevation_north.svg", "elevation_east.svg", "elevation_south.svg", "elevation_west.svg",
                "section_AA.svg", "section_BB.svg", "site_plan.svg",
            ]:
                p = drawings / name
                p.write_text("<svg/>", encoding="utf-8")
                paths.append(p.relative_to(repo).as_posix())
            state = {
                "capabilities": {
                    "architecture": {"status": "PASSED", "outputs": paths},
                    "structural_engineering": {"status": "BLOCKED", "outputs": []},
                    "closure": {"status": "PASSED", "outputs": []},
                }
            }
            (ws / "orchestration").mkdir(parents=True)
            (ws / "orchestration" / "adapter_state.json").write_text(json.dumps(state), encoding="utf-8")
            manifest = build_minimum_deliverable_manifest(self.ctx(repo, ws, ws / "results" / "session_adapters" / "closure"))
            by_id = {x["id"]: x for x in manifest["items"]}
            self.assertEqual(by_id["B01_FLOOR_PLAN"]["status"], "GENERATED_AND_VALIDATED")
            self.assertEqual(by_id["B04_B05_FACADES"]["status"], "GENERATED_AND_VALIDATED")
            self.assertEqual(by_id["B07_SECTIONS"]["status"], "GENERATED_AND_VALIDATED")
            self.assertEqual(by_id["S01_SITE_PLAN"]["status"], "GENERATED_AND_VALIDATED")
            self.assertEqual(by_id["B12_WATER_PLAN"]["status"], "BLOCKED_WITH_EXPLICIT_REASON")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
