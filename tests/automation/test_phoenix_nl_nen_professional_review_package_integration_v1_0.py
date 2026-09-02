import json
from pathlib import Path
import tempfile
import unittest

from phoenix.autonomy.nl_nen_professional_review_package_integration import (
    build_professional_review_package,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
