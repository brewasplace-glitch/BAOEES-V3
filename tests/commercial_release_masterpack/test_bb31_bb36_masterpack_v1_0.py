from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.commercial_release_masterpack import (
    AutonomousBuildingPackageEngine,
    CommercialProductShellEngine,
    CommercialReleaseEngine,
    CommercialReleaseMasterpackExporter,
    MasterpackOrchestrator,
    RealProjectValidationEngine,
    ReleaseCandidateEngine,
    SecurityDataProtectionEngine,
)


def clean_deliverables():
    return {
        name: {
            "professional_review_passed": True,
            "quality_score": 90,
        }
        for name in (
            "3d_impression",
            "structural_calculations",
            "structural_report",
            "building_drawings",
            "technical_specification",
            "specification_drawings",
            "cost_calculation",
            "material_schedules",
            "site_plan",
        )
    }


class MasterpackTests(unittest.TestCase):
    def test_bb31_clean_project(self):
        report = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        self.assertTrue(report["project_shell_passed"])

    def test_bb31_missing_name_blocks(self):
        report = CommercialProductShellEngine().create_project(
            {"project_id": "P1"}
        )
        self.assertFalse(report["project_shell_passed"])

    def test_bb31_defaults_to_usd(self):
        report = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        self.assertEqual("USD", report["currency"])

    def test_bb31_has_nine_outputs(self):
        report = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        self.assertEqual(9, len(report["requested_deliverables"]))

    def test_bb32_plan_requires_inputs(self):
        shell = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        plan = AutonomousBuildingPackageEngine().create_execution_plan(
            shell, available_inputs=["project_brief"]
        )
        self.assertFalse(plan["execution_plan_passed"])

    def test_bb32_plan_passes_with_inputs(self):
        shell = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        plan = AutonomousBuildingPackageEngine().create_execution_plan(
            shell,
            available_inputs=["project_brief", "site_information"],
        )
        self.assertTrue(plan["execution_plan_passed"])

    def test_bb32_execute_all_adapters(self):
        shell = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        engine = AutonomousBuildingPackageEngine()
        plan = engine.create_execution_plan(
            shell,
            available_inputs=["project_brief", "site_information"],
        )
        adapter = lambda payload: {"file": payload["deliverable_type"] + ".pdf"}
        execution = engine.execute(
            plan,
            adapters={
                "visualization_adapter": adapter,
                "structural_adapter": adapter,
                "drawing_adapter": adapter,
                "specification_adapter": adapter,
                "cost_adapter": adapter,
                "quantity_adapter": adapter,
            },
        )
        self.assertTrue(execution["execution_passed"])
        self.assertEqual(9, execution["result_count"])

    def test_bb32_missing_runtime_adapter_blocks(self):
        shell = CommercialProductShellEngine().create_project(
            {"project_id": "P1", "project_name": "Pilot"}
        )
        engine = AutonomousBuildingPackageEngine()
        plan = engine.create_execution_plan(
            shell,
            available_inputs=["project_brief", "site_information"],
        )
        execution = engine.execute(plan, adapters={})
        self.assertFalse(execution["execution_passed"])

    def test_bb33_permissions(self):
        engine = SecurityDataProtectionEngine()
        self.assertTrue(engine.authorize("administrator", "security:manage"))
        self.assertFalse(engine.authorize("viewer", "design:run"))

    def test_bb33_integrity_manifest(self):
        manifest = SecurityDataProtectionEngine().create_integrity_manifest(
            {"a.txt": "hello"}
        )
        self.assertEqual(1, manifest["file_count"])

    def test_bb33_audit_chain(self):
        engine = SecurityDataProtectionEngine()
        chain = engine.append_audit_event(
            [], actor="user", action="create", target="P1", timestamp="2026-01-01T00:00:00Z"
        )
        chain = engine.append_audit_event(
            chain, actor="user", action="review", target="P1", timestamp="2026-01-02T00:00:00Z"
        )
        self.assertTrue(engine.verify_audit_chain(chain))

    def test_bb33_security_report(self):
        engine = SecurityDataProtectionEngine()
        chain = engine.append_audit_event(
            [], actor="user", action="create", target="P1", timestamp="2026-01-01T00:00:00Z"
        )
        report = engine.create_security_report(
            audit_chain=chain,
            integrity_manifest=engine.create_integrity_manifest({"a": "b"}),
            backup_tested=True,
            restore_tested=True,
        )
        self.assertTrue(report["security_passed"])

    def test_bb34_release_candidate_passes(self):
        report = ReleaseCandidateEngine().create_release_candidate(
            version="2.0.0-rc.1",
            component_status={
                "commercial_product_shell": True,
                "autonomous_building_package": True,
                "security_data_protection": True,
                "commercial_delivery_orchestrator": True,
            },
            regression_passed=True,
            clean_install_tested=True,
            update_tested=True,
            migration_tested=True,
            rollback_tested=True,
            license_policy_present=True,
            user_guide_present=True,
        )
        self.assertTrue(report["release_candidate_passed"])

    def test_bb34_invalid_version_blocks(self):
        report = ReleaseCandidateEngine().create_release_candidate(
            version="release",
            component_status={},
            regression_passed=False,
            clean_install_tested=False,
            update_tested=False,
            migration_tested=False,
            rollback_tested=False,
            license_policy_present=False,
            user_guide_present=False,
        )
        self.assertFalse(report["release_candidate_passed"])

    def test_bb35_synthetic_project_rejected(self):
        report = RealProjectValidationEngine().validate([{
            "project_id": "P1",
            "real_project": False,
            "independent_reviewer": "Reviewer",
            "clean_install_tested": True,
            "reproducibility_passed": True,
            "end_to_end_run_passed": True,
            "deliverables": clean_deliverables(),
        }])
        self.assertFalse(report["real_project_validation_passed"])

    def test_bb35_one_real_project_insufficient(self):
        report = RealProjectValidationEngine().validate([{
            "project_id": "P1",
            "real_project": True,
            "independent_reviewer": "Reviewer",
            "clean_install_tested": True,
            "reproducibility_passed": True,
            "end_to_end_run_passed": True,
            "deliverables": clean_deliverables(),
        }])
        self.assertFalse(report["real_project_validation_passed"])

    def test_bb35_two_real_projects_pass(self):
        pilots = []
        for project_id in ("P1", "P2"):
            pilots.append({
                "project_id": project_id,
                "real_project": True,
                "independent_reviewer": "Reviewer",
                "clean_install_tested": True,
                "reproducibility_passed": True,
                "end_to_end_run_passed": True,
                "deliverables": clean_deliverables(),
            })
        report = RealProjectValidationEngine().validate(pilots)
        self.assertTrue(report["real_project_validation_passed"])

    def test_bb35_low_quality_blocks(self):
        deliverables = clean_deliverables()
        deliverables["site_plan"]["quality_score"] = 50
        report = RealProjectValidationEngine().validate([{
            "project_id": "P1",
            "real_project": True,
            "independent_reviewer": "Reviewer",
            "clean_install_tested": True,
            "reproducibility_passed": True,
            "end_to_end_run_passed": True,
            "deliverables": deliverables,
        }], minimum_pilots=1)
        self.assertFalse(report["real_project_validation_passed"])

    @staticmethod
    def _r6_pass_report():
        variants = []
        for variant_id in "ABCDE":
            variants.append({
                "variant_id": variant_id,
                "result": {
                    "hard_pass": True,
                    "hard_failures": [],
                    "tolerance_m": 0.35,
                    "match_coverage": 1.0,
                    "max_center_difference_m": 0.0,
                    "max_width_difference_m": 0.0,
                    "max_depth_difference_m": 0.0,
                    "ifc": {
                        "schema_error_count": 0,
                        "geometry_failure_count": 0,
                        "geometric_space_count": 12,
                        "wall_count": 27,
                    },
                },
            })
        return {
            "schema": "PHOENIX_R6_RUNTIME_CANONICAL_GEOMETRY_QA_V1",
            "baseline": "test-baseline",
            "run_id": "test-r6-run",
            "hard_pass": True,
            "release_gate_candidate": True,
            "variants": variants,
        }

    def test_bb36_locked_without_validation(self):
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": False},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
        )
        self.assertFalse(report["production_release_ready"])

    def test_bb36_releases_when_all_pass(self):
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": True},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
            r6_canonical_geometry_report=self._r6_pass_report(),
        )
        self.assertTrue(report["production_release_ready"])
        self.assertTrue(report["checks"]["r6_canonical_geometry_passed"])
        self.assertFalse(report["release_semantics"]["professional_approval_inferred"])
        self.assertFalse(report["release_semantics"]["approved_for_construction_inferred"])

    def test_bb36_missing_r6_canonical_geometry_locks(self):
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": True},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
        )
        self.assertFalse(report["production_release_ready"])
        self.assertIn("r6_canonical_geometry_passed", report["failed_checks"])
        self.assertFalse(report["r6_canonical_geometry_gate"]["passed"])

    def test_bb36_failed_r6_canonical_geometry_locks(self):
        r6 = self._r6_pass_report()
        r6["variants"][0]["result"]["max_center_difference_m"] = 1.0
        report = CommercialReleaseEngine().create_release(
            version="2.0.0",
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": True},
            security_report={"security_passed": True},
            documentation_available=True,
            support_plan_available=True,
            release_requested=True,
            r6_canonical_geometry_report=r6,
        )
        self.assertFalse(report["production_release_ready"])
        self.assertIn("r6_canonical_geometry_passed", report["failed_checks"])
        self.assertFalse(report["r6_canonical_geometry_gate"]["passed"])

    def test_masterpack_framework_can_install_while_release_locked(self):
        report = MasterpackOrchestrator().create_framework_report(
            shell_report={"project_shell_passed": True},
            execution_report={"execution_passed": True},
            security_report={"security_passed": True},
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": False},
            production_release_report={"production_release_ready": False},
        )
        self.assertTrue(report["framework_installed"])
        self.assertTrue(report["production_release_locked"])

    def test_masterpack_fingerprint_is_deterministic(self):
        engine = MasterpackOrchestrator()
        kwargs = dict(
            shell_report={"project_shell_passed": True},
            execution_report={"execution_passed": True},
            security_report={"security_passed": True},
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": False},
            production_release_report={"production_release_ready": False},
        )
        first = engine.create_framework_report(**kwargs)
        second = engine.create_framework_report(**kwargs)
        self.assertEqual(
            first["masterpack_fingerprint_sha256"],
            second["masterpack_fingerprint_sha256"],
        )

    def test_exports_create_five_files(self):
        report = MasterpackOrchestrator().create_framework_report(
            shell_report={"project_shell_passed": True},
            execution_report={"execution_passed": True},
            security_report={"security_passed": True},
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": False},
            production_release_report={"production_release_ready": False},
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = CommercialReleaseMasterpackExporter().export_all(report, tmp)
            self.assertEqual(5, len(paths))
            self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_dossier_structure(self):
        report = MasterpackOrchestrator().create_framework_report(
            shell_report={"project_shell_passed": True},
            execution_report={"execution_passed": True},
            security_report={"security_passed": True},
            release_candidate_report={"release_candidate_passed": True},
            validation_report={"real_project_validation_passed": False},
            production_release_report={"production_release_ready": False},
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = CommercialReleaseMasterpackExporter().export_all(report, tmp)
            with zipfile.ZipFile(paths["dossier"]) as archive:
                names = set(archive.namelist())
            self.assertIn("commercial_release_masterpack_report.json", names)
            self.assertIn("phoenix_commercial_release_dashboard.html", names)


if __name__ == "__main__":
    unittest.main()
