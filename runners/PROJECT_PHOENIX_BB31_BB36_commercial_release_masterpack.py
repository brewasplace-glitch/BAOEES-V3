"""Integrated BB31-BB36 self-test with BB35/BB36 deliberately locked."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    shell = CommercialProductShellEngine().create_project({
        "project_id": "PHX-BB31-BB36-SELFTEST",
        "project_name": "Phoenix Commercial Release Self-Test",
        "currency": "USD",
    })

    autonomous = AutonomousBuildingPackageEngine()
    plan = autonomous.create_execution_plan(
        shell,
        available_inputs=["project_brief", "site_information"],
    )
    adapter = lambda payload: {
        "file_name": payload["deliverable_type"] + ".pdf",
        "revision": "P01",
        "synthetic_selftest": True,
    }
    execution = autonomous.execute(
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

    security_engine = SecurityDataProtectionEngine()
    chain = security_engine.append_audit_event(
        [],
        actor="selftest",
        action="create",
        target=shell["project_id"],
        timestamp="2026-01-01T00:00:00Z",
    )
    chain = security_engine.append_audit_event(
        chain,
        actor="selftest",
        action="review",
        target=shell["project_id"],
        timestamp="2026-01-02T00:00:00Z",
    )
    security = security_engine.create_security_report(
        audit_chain=chain,
        integrity_manifest=security_engine.create_integrity_manifest({
            item["deliverable_type"]: json.dumps(item, sort_keys=True)
            for item in execution["results"]
        }),
        backup_tested=True,
        restore_tested=True,
    )

    release_candidate = ReleaseCandidateEngine().create_release_candidate(
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

    validation = RealProjectValidationEngine().validate([])
    production = CommercialReleaseEngine().create_release(
        version="2.0.0",
        release_candidate_report=release_candidate,
        validation_report=validation,
        security_report=security,
        documentation_available=True,
        support_plan_available=True,
        release_requested=True,
    )

    report = MasterpackOrchestrator().create_framework_report(
        shell_report=shell,
        execution_report=execution,
        security_report=security,
        release_candidate_report=release_candidate,
        validation_report=validation,
        production_release_report=production,
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir
    paths = CommercialReleaseMasterpackExporter().export_all(report, output_dir)

    with zipfile.ZipFile(paths["dossier"]) as archive:
        dossier_ok = {
            "commercial_release_masterpack_report.json",
            "commercial_release_gate_matrix.csv",
            "phoenix_commercial_release_dashboard.html",
            "checksums.sha256",
            "PACKAGE_README.txt",
        }.issubset(set(archive.namelist()))

    passed = (
        shell["project_shell_passed"]
        and execution["execution_passed"]
        and len(execution["results"]) == 9
        and security["security_passed"]
        and release_candidate["release_candidate_passed"]
        and not validation["real_project_validation_passed"]
        and not production["production_release_ready"]
        and report["framework_installed"]
        and report["pilot_validation_pending"]
        and report["production_release_locked"]
        and dossier_ok
    )

    print(json.dumps({
        "status": "PASSED" if passed else "FAILED",
        "bb31_product_shell_passed": shell["project_shell_passed"],
        "bb32_autonomous_generator_passed": execution["execution_passed"],
        "bb32_deliverable_count": len(execution["results"]),
        "bb33_security_passed": security["security_passed"],
        "bb34_release_candidate_framework_passed": (
            release_candidate["release_candidate_passed"]
        ),
        "bb35_real_project_validation_passed": (
            validation["real_project_validation_passed"]
        ),
        "bb36_production_release_ready": production["production_release_ready"],
        "framework_installed": report["framework_installed"],
        "production_release_locked_as_required": (
            report["production_release_locked"]
        ),
        "dossier_valid": dossier_ok,
        "output_dir": str(output_dir),
    }, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
