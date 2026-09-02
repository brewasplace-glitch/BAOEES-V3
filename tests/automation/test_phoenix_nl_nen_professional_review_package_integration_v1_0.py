import json
from pathlib import Path
import tempfile
import unittest

from phoenix.autonomy.nl_nen_professional_review_package_integration import (
    build_professional_review_package,
    build_structural_review_input_pack,
    prepare_nl_professional_review_basis,
)

ROOT = Path(__file__).resolve().parents[2]


class NLNENProfessionalReviewIntegrationTests(unittest.TestCase):
    def test_01_nl_binding_installs_review_candidate_for_v82(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "results/session_adapters/structural_engineering"
            context = workspace / "results/session_adapters/architecture/project_context.json"
            context.parent.mkdir(parents=True)
            context.write_text(json.dumps({"facts": {"country_code": "NL"}}), encoding="utf-8")
            result = prepare_nl_professional_review_basis(
                repository=ROOT,
                session={"selected_project": "MOSKEE-BUNSCHOTEN-E2E-REAL-001"},
                workspace=workspace,
                output_dir=output,
                project_context_path=context,
            )
            self.assertEqual(result["status"], "PASSED_FOR_PROFESSIONAL_REVIEW_PACKAGE")
            value = json.loads(result["input"].read_text(encoding="utf-8"))
            self.assertEqual(value["basis"], "NL_NEN_BIB_PROFESSIONAL_REVIEW_CANDIDATE")
            self.assertEqual(len(value["actions"]), 2)
            self.assertEqual(len(value["combinations"]), 3)
            self.assertFalse(value["formal_release"])
            self.assertFalse(any(row.get("limit_state") == "ULS" for row in value["combinations"]))

    def test_02_non_nl_project_is_not_modified(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            context = workspace / "context.json"
            context.parent.mkdir(parents=True)
            context.write_text(json.dumps({"facts": {"country_code": "SR"}}), encoding="utf-8")
            result = prepare_nl_professional_review_basis(
                repository=ROOT,
                session={"selected_project": "OTHER"},
                workspace=workspace,
                output_dir=workspace / "output",
                project_context_path=context,
            )
            self.assertEqual(result["status"], "NOT_APPLICABLE")
            self.assertFalse((workspace / "inputs/structural/action_load_input_REQUIRED.json").exists())

    def test_03_complete_review_evidence_creates_locked_package(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "results/session_adapters/structural_engineering"
            samples = {
                "reports/structural_calculation_report.json": {},
                "drawings/structural_drawing.svg": "<svg/>",
                "details/member_detail_and_dimensions.json": {},
                "registers/action_load_combination_register.json": {},
                "schedules/material_section_schedule.csv": "id\n",
                "specification/technical_specification.md": "# spec\n",
                "qaqc/structural_qaqc_report.json": {},
                "registers/assumptions_sources_deviations_register.json": {},
                "models/structural_model.json": {},
                "solver/calculix_LC-G.inp": "*HEADING\n",
            }
            for rel, value in samples.items():
                path = workspace / "results" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding="utf-8")
            result = build_professional_review_package(
                repository=ROOT, workspace=workspace, output_dir=output, project_id="P1"
            )
            self.assertEqual(result["status"], "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW")
            self.assertEqual(result["missing_required_outputs"], [])
            self.assertTrue(result["zip"].is_file())
            manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(manifest["not_for_construction"])
            self.assertEqual(manifest["formal_release"], "LOCKED")

    def test_04_incomplete_package_fails_closed_but_writes_manifest_and_zip(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "output"
            workspace.mkdir(parents=True)
            result = build_professional_review_package(
                repository=ROOT, workspace=workspace, output_dir=output, project_id="P1"
            )
            self.assertEqual(result["status"], "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW_INCOMPLETE")
            self.assertTrue(result["missing_required_outputs"])
            self.assertTrue(result["manifest"].is_file())
            self.assertTrue(result["zip"].is_file())

    def test_05_session_adapter_has_production_wiring(self):
        source = (ROOT / "phoenix/autonomy/session_adapters.py").read_text(encoding="utf-8-sig")
        self.assertIn("PHOENIX_NL_NEN_PROFESSIONAL_REVIEW_INTEGRATION_v1_0", source)
        self.assertIn("prepare_nl_professional_review_basis", source)
        self.assertIn("build_professional_review_package", source)

    def test_06_standalone_runner_bootstraps_repository_imports(self):
        source = (
            ROOT / "runners/PROJECT_PHOENIX_moskee_level_a_professional_review_package_v1_0.py"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("REPOSITORY_BOOTSTRAP = Path(__file__).resolve().parents[1]", source)
        self.assertIn("sys.path.insert(0, str(REPOSITORY_BOOTSTRAP))", source)

    def test_07_runner_uses_authoritative_architectural_runtime_entrypoint(self):
        source = (
            ROOT / "runners/PROJECT_PHOENIX_moskee_level_a_professional_review_package_v1_0.py"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("ArchitecturalOrchestrationRuntime", source)
        self.assertIn("runtime.start(args.project_json)", source)
        self.assertIn('bridge_root = job_root / "structural_session_bridge"', source)
        self.assertNotIn("project_orchestration_cli", source)


    def test_08_source_derived_pack_records_missing_elements_without_invention(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "results/session_adapters/structural_engineering"
            required = workspace / "inputs/structural/structural_analysis_basis_REQUIRED.json"
            required.parent.mkdir(parents=True)
            required.write_text(json.dumps({"blockers": [{"reason": "INPUT_REQUIRED", "missing_element_ids": ["M0001"]}]}), encoding="utf-8")
            action = workspace / "inputs/structural/action_load_input_REQUIRED.json"
            action.write_text(json.dumps({"basis": "NL_NEN_BIB_PROFESSIONAL_REVIEW_CANDIDATE", "explicit_unresolved_items": ["ULS_MAPPING"]}), encoding="utf-8")
            model = output / "v8_0_structural_derivation/model/structural_candidate_model.json"
            model.parent.mkdir(parents=True)
            model.write_text(json.dumps({"elements": [{"id": "M0001", "material": "GENERIC"}]}), encoding="utf-8")
            result = build_structural_review_input_pack(repository=ROOT, workspace=workspace, output_dir=output, project_id="P1")
            self.assertEqual(result["status"], "REVIEW_INPUT_REQUIRED")
            pack = json.loads(result["pack"].read_text(encoding="utf-8"))
            self.assertEqual(pack["invented_values"], [])
            self.assertFalse(pack["solver_execution_allowed"])
            self.assertEqual(pack["missing_element_count"], 1)
            self.assertEqual(pack["element_input_schedule"][0]["source_derived_values"], {})
            self.assertTrue(result["technical_specification"].is_file())
            self.assertTrue(result["qaqc"].is_file())

    def test_09_solver_register_does_not_count_as_solver_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "results/session_adapters/structural_engineering"
            solver = output / "validated/v8_3/autonomous_solver_basis_register.json"
            solver.parent.mkdir(parents=True)
            solver.write_text("{}", encoding="utf-8")
            result = build_professional_review_package(repository=ROOT, workspace=workspace, output_dir=output, project_id="P1")
            self.assertIn("solver_evidence", result["missing_required_outputs"])

    def test_10_archive_names_are_unique_and_identical_same_name_sources_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            output = workspace / "results/session_adapters/structural_engineering"
            samples = {
                "reports/structural_calculation_report.json": "calc",
                "drawings/structural_drawing.svg": "<svg/>",
                "details/member_detail_and_dimensions.json": "detail",
                "registers/action_load_combination_register.json": "loads",
                "schedules/material_section_schedule.csv": "schedule",
                "specification/technical_specification.md": "spec",
                "qaqc/structural_qaqc_report.json": "qaqc",
                "registers/assumptions_sources_deviations_register.json": "register",
                "models/a/central_project_digital_twin.json": "same-twin",
                "models/b/central_project_digital_twin.json": "same-twin",
                "solver/calculix_LC-G.inp": "*HEADING",
            }
            for rel, value in samples.items():
                path = workspace / "results" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value, encoding="utf-8")
            result = build_professional_review_package(repository=ROOT, workspace=workspace, output_dir=output, project_id="P1")
            self.assertEqual(result["deduplicated_source_count"], 1)
            import zipfile
            with zipfile.ZipFile(result["zip"]) as archive:
                names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))

    def test_11_session_adapter_wires_source_derived_pack_before_package(self):
        source = (ROOT / "phoenix/autonomy/session_adapters.py").read_text(encoding="utf-8-sig")
        self.assertIn("build_structural_review_input_pack", source)
        self.assertLess(source.index("nl_review_input_pack=build_structural_review_input_pack"), source.index("nl_review_package=build_professional_review_package"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
