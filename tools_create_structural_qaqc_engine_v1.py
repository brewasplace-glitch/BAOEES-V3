from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/structural_qaqc_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import StructuralQAQCEngine\n"

MAIN_CONTENT = '''from datetime import datetime


class StructuralQAQCEngine:

    def __init__(self):
        self.qaqc_result = {}

    def create_structural_qaqc_review(
        self,
        project_result=None,
        building_technical_result=None,
        structural_load_result=None,
        element_load_result=None,
        foundation_load_transfer_result=None,
        foundation_design_result=None,
        foundation_verification_result=None,
        structural_element_sizing_result=None,
        structural_reinforcement_result=None,
        structural_calculation_report_result=None,
        structural_drawing_package_result=None,
        structural_cad_export_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        building_technical_result = building_technical_result or {}
        structural_load_result = structural_load_result or {}
        element_load_result = element_load_result or {}
        foundation_load_transfer_result = foundation_load_transfer_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_verification_result = foundation_verification_result or {}
        structural_element_sizing_result = structural_element_sizing_result or {}
        structural_reinforcement_result = structural_reinforcement_result or {}
        structural_calculation_report_result = structural_calculation_report_result or {}
        structural_drawing_package_result = structural_drawing_package_result or {}
        structural_cad_export_result = structural_cad_export_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        source_statuses = self.build_source_statuses(
            building_technical_result,
            structural_load_result,
            element_load_result,
            foundation_load_transfer_result,
            foundation_design_result,
            foundation_verification_result,
            structural_element_sizing_result,
            structural_reinforcement_result,
            structural_calculation_report_result,
            structural_drawing_package_result,
            structural_cad_export_result
        )

        data_flow_checks = self.build_data_flow_checks(source_statuses)

        consistency_checks = self.build_consistency_checks(
            structural_load_result,
            element_load_result,
            foundation_design_result,
            foundation_verification_result,
            structural_element_sizing_result,
            structural_reinforcement_result,
            structural_drawing_package_result,
            structural_cad_export_result
        )

        completeness_checks = self.build_completeness_checks(
            structural_calculation_report_result,
            structural_drawing_package_result,
            structural_cad_export_result
        )

        critical_findings = self.build_critical_findings(
            data_flow_checks,
            consistency_checks,
            completeness_checks
        )

        approval_status = self.build_approval_status(critical_findings)

        self.qaqc_result = {
            "engine": "StructuralQAQCEngine",
            "version": "1.0",
            "status": "STRUCTURAL_QAQC_REVIEW_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "review_level": "concept constructieve ketencontrole",
            "source_statuses": source_statuses,
            "data_flow_checks": data_flow_checks,
            "consistency_checks": consistency_checks,
            "completeness_checks": completeness_checks,
            "critical_findings": critical_findings,
            "approval_status": approval_status,
            "digital_twin_update": {
                "digital_twin_node": "structural_qaqc_review",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "source_statuses": source_statuses,
                    "data_flow_checks": data_flow_checks,
                    "consistency_checks": consistency_checks,
                    "completeness_checks": completeness_checks,
                    "critical_findings": critical_findings,
                    "approval_status": approval_status
                }
            },
            "warnings": self.build_warnings(critical_findings, approval_status),
            "recommendation": {
                "status": "STRUCTURAL_QAQC_ADVIES",
                "advice": (
                    "Gebruik deze QA/QC-review als laatste controle op de constructieve "
                    "conceptketen voordat rapportage, tekeningen en CAD-export definitief "
                    "worden vrijgegeven."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.qaqc_result

    def build_source_statuses(self, *results):
        names = [
            "building_technical",
            "structural_loads",
            "element_loads",
            "foundation_load_transfer",
            "foundation_design",
            "foundation_verification",
            "structural_element_sizing",
            "structural_reinforcement",
            "structural_calculation_report",
            "structural_drawing_package",
            "structural_cad_export"
        ]

        statuses = {}

        for name, result in zip(names, results):
            statuses[name] = result.get("status", "ONTBREEKT") if result else "ONTBREEKT"

        return statuses

    def build_data_flow_checks(self, source_statuses):
        required_order = [
            "building_technical",
            "structural_loads",
            "element_loads",
            "foundation_load_transfer",
            "foundation_design",
            "foundation_verification",
            "structural_element_sizing",
            "structural_reinforcement",
            "structural_calculation_report",
            "structural_drawing_package",
            "structural_cad_export"
        ]

        checks = []

        for item in required_order:
            status = source_statuses.get(item, "ONTBREEKT")

            checks.append(
                {
                    "check": item,
                    "source_status": status,
                    "status": "OK" if status != "ONTBREEKT" else "AANDACHT"
                }
            )

        return checks

    def build_consistency_checks(
        self,
        structural_load_result,
        element_load_result,
        foundation_design_result,
        foundation_verification_result,
        structural_element_sizing_result,
        structural_reinforcement_result,
        structural_drawing_package_result,
        structural_cad_export_result
    ):
        checks = []

        checks.append(
            {
                "check": "belastingen_naar_elementlasten",
                "status": "OK" if structural_load_result and element_load_result else "AANDACHT"
            }
        )

        checks.append(
            {
                "check": "fundering_ontwerp_en_controle",
                "status": "OK" if foundation_design_result and foundation_verification_result else "AANDACHT"
            }
        )

        checks.append(
            {
                "check": "elementafmetingen_naar_wapening",
                "status": "OK" if structural_element_sizing_result and structural_reinforcement_result else "AANDACHT"
            }
        )

        checks.append(
            {
                "check": "tekeningen_naar_cad_export",
                "status": "OK" if structural_drawing_package_result and structural_cad_export_result else "AANDACHT"
            }
        )

        return checks

    def build_completeness_checks(
        self,
        structural_calculation_report_result,
        structural_drawing_package_result,
        structural_cad_export_result
    ):
        return [
            {
                "check": "berekeningssamenvatting_beschikbaar",
                "status": "OK" if structural_calculation_report_result else "AANDACHT"
            },
            {
                "check": "constructietekenpakket_beschikbaar",
                "status": "OK" if structural_drawing_package_result else "AANDACHT"
            },
            {
                "check": "cad_exportpakket_beschikbaar",
                "status": "OK" if structural_cad_export_result else "AANDACHT"
            }
        ]

    def build_critical_findings(
        self,
        data_flow_checks,
        consistency_checks,
        completeness_checks
    ):
        findings = []

        for group_name, checks in [
            ("data_flow", data_flow_checks),
            ("consistency", consistency_checks),
            ("completeness", completeness_checks)
        ]:
            for check in checks:
                if check.get("status") == "AANDACHT":
                    findings.append(
                        {
                            "group": group_name,
                            "check": check.get("check"),
                            "severity": "medium",
                            "message": f"Controle vraagt aandacht: {check.get('check')}"
                        }
                    )

        return findings

    def build_approval_status(self, critical_findings):
        if not critical_findings:
            return {
                "status": "CONCEPT_KETEN_QAQC_OK",
                "can_continue_to_document_export": True,
                "can_continue_to_definitive_engineering": False
            }

        return {
            "status": "CONCEPT_KETEN_QAQC_AANDACHT",
            "can_continue_to_document_export": True,
            "can_continue_to_definitive_engineering": False
        }

    def build_warnings(self, critical_findings, approval_status):
        warnings = []

        for finding in critical_findings:
            warnings.append(finding.get("message"))

        if approval_status.get("can_continue_to_definitive_engineering") is False:
            warnings.append(
                "Definitieve engineering vereist nog normatieve berekeningen en constructeurcontrole."
            )

        if not warnings:
            warnings.append("Geen kritieke QA/QC-waarschuwingen in de constructieve conceptketen.")

        return warnings

    def get_qaqc_result(self):
        return self.qaqc_result

    def create_qaqc_review(self, *args, **kwargs):
        return self.create_structural_qaqc_review(*args, **kwargs)

    def generate_structural_qaqc_review(self, *args, **kwargs):
        return self.create_structural_qaqc_review(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_qaqc_review(*args, **kwargs)
'''


def run_command(command, check=True):
    print("")
    print(f">> {command}")

    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def write_files():
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.structural_qaqc_engine.main")
    engine_class = getattr(module, "StructuralQAQCEngine")
    engine = engine_class()

    ok_statuses = {
        "status": "OK"
    }

    result = engine.create_structural_qaqc_review(
        project_result={"project_id": "test", "project_name": "Testproject"},
        building_technical_result=ok_statuses,
        structural_load_result=ok_statuses,
        element_load_result=ok_statuses,
        foundation_load_transfer_result=ok_statuses,
        foundation_design_result=ok_statuses,
        foundation_verification_result=ok_statuses,
        structural_element_sizing_result=ok_statuses,
        structural_reinforcement_result=ok_statuses,
        structural_calculation_report_result=ok_statuses,
        structural_drawing_package_result=ok_statuses,
        structural_cad_export_result=ok_statuses
    )

    if result.get("status") != "STRUCTURAL_QAQC_REVIEW_GEREED":
        raise RuntimeError("Structural QA/QC Engine gaf geen correcte status terug.")

    if len(result.get("data_flow_checks", [])) < 10:
        raise RuntimeError("Structural QA/QC Engine genereerde te weinig controles.")

    print("")
    print("STRUCTURAL_QAQC_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Aantal dataflow checks: {len(result.get('data_flow_checks', []))}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("STRUCTURAL_QAQC_ENGINE_V1_AANGEMAAKT")


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)
    run_command("git restore outputs", check=False)

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("BAOEES_TEST_NIET_OK")
        raise SystemExit(1)

    print("")
    print("BAOEES_TEST_OK")


def commit():
    create_test()
    test_baoees()

    run_command("git restore outputs", check=False)
    run_command("git add baoees/structural_qaqc_engine/__init__.py")
    run_command("git add baoees/structural_qaqc_engine/main.py")
    run_command("git add tools_create_structural_qaqc_engine_v1.py")
    run_command('git commit -m "feat: add Structural QAQC Engine v1"')
    run_command("git push")
    run_command("git status", check=False)


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "status",
            "create-test",
            "test-baoees",
            "commit"
        ]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "create-test":
        create_test()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit":
        commit()


if __name__ == "__main__":
    main()
