from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/structural_project_output_package_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import StructuralProjectOutputPackageEngine\n"

MAIN_CONTENT = """from datetime import datetime


class StructuralProjectOutputPackageEngine:

    def __init__(self):
        self.output_package_result = {}

    def create_structural_project_output_package(
        self,
        project_result=None,
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
        structural_qaqc_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
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
        structural_qaqc_result = structural_qaqc_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        package_manifest = self.build_package_manifest(project_id, project_name)
        source_statuses = self.build_source_statuses(
            structural_load_result,
            element_load_result,
            foundation_load_transfer_result,
            foundation_design_result,
            foundation_verification_result,
            structural_element_sizing_result,
            structural_reinforcement_result,
            structural_calculation_report_result,
            structural_drawing_package_result,
            structural_cad_export_result,
            structural_qaqc_result
        )
        document_outputs = self.build_document_outputs(
            structural_calculation_report_result,
            structural_drawing_package_result,
            structural_cad_export_result
        )
        data_outputs = self.build_data_outputs(
            structural_load_result,
            element_load_result,
            foundation_load_transfer_result,
            foundation_design_result,
            foundation_verification_result,
            structural_element_sizing_result,
            structural_reinforcement_result,
            structural_qaqc_result
        )
        folder_structure = self.build_folder_structure()
        qa_qc_checks = self.build_qa_qc_checks(source_statuses, document_outputs, data_outputs)
        final_readiness = self.build_final_readiness(qa_qc_checks)

        self.output_package_result = {
            "engine": "StructuralProjectOutputPackageEngine",
            "version": "1.0",
            "status": "STRUCTURAL_PROJECT_OUTPUT_PACKAGE_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "package_manifest": package_manifest,
            "source_statuses": source_statuses,
            "document_outputs": document_outputs,
            "data_outputs": data_outputs,
            "folder_structure": folder_structure,
            "qa_qc_checks": qa_qc_checks,
            "final_readiness": final_readiness,
            "digital_twin_update": {
                "digital_twin_node": "structural_project_output_package",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "package_manifest": package_manifest,
                    "source_statuses": source_statuses,
                    "document_outputs": document_outputs,
                    "data_outputs": data_outputs,
                    "folder_structure": folder_structure,
                    "final_readiness": final_readiness
                }
            },
            "warnings": self.build_warnings(qa_qc_checks, final_readiness),
            "recommendation": {
                "status": "STRUCTURAL_OUTPUT_PACKAGE_ADVIES",
                "advice": (
                    "Gebruik dit pakket als centraal constructief concept-outputpakket. "
                    "Voor definitieve indiening zijn normatieve berekeningen, echte CAD/BIM-bestanden, "
                    "projectspecifieke maatvoering en constructeurcontrole nodig."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.output_package_result

    def build_package_manifest(self, project_id, project_name):
        safe_name = self.safe_name(project_name)

        return {
            "package_name": f"{safe_name}_constructief_outputpakket",
            "project_id": project_id,
            "project_name": project_name,
            "status": "MANIFEST_GEREED",
            "package_type": "constructief conceptpakket",
            "version": "1.0"
        }

    def build_source_statuses(self, *items):
        names = [
            "structural_loads",
            "element_loads",
            "foundation_load_transfer",
            "foundation_design",
            "foundation_verification",
            "structural_element_sizing",
            "structural_reinforcement",
            "structural_calculation_report",
            "structural_drawing_package",
            "structural_cad_export",
            "structural_qaqc"
        ]

        statuses = {}

        for name, item in zip(names, items):
            statuses[name] = item.get("status", "ONTBREEKT") if item else "ONTBREEKT"

        return statuses

    def build_document_outputs(
        self,
        structural_calculation_report_result,
        structural_drawing_package_result,
        structural_cad_export_result
    ):
        return {
            "calculation_report": {
                "status": structural_calculation_report_result.get("status", "ONTBREEKT"),
                "formats": ["PDF", "DOCX", "JSON"]
            },
            "drawing_package": {
                "status": structural_drawing_package_result.get("status", "ONTBREEKT"),
                "formats": ["PDF", "DXF", "DWG", "IFC"]
            },
            "cad_export": {
                "status": structural_cad_export_result.get("status", "ONTBREEKT"),
                "formats": ["PDF", "DXF", "DWG", "IFC", "FreeCAD", "JSON"]
            }
        }

    def build_data_outputs(
        self,
        structural_load_result,
        element_load_result,
        foundation_load_transfer_result,
        foundation_design_result,
        foundation_verification_result,
        structural_element_sizing_result,
        structural_reinforcement_result,
        structural_qaqc_result
    ):
        return {
            "json_sources": [
                "structural_loads.json",
                "element_loads.json",
                "foundation_load_transfer.json",
                "foundation_design.json",
                "foundation_verification.json",
                "structural_element_sizing.json",
                "structural_reinforcement.json",
                "structural_qaqc_review.json"
            ],
            "digital_twin_nodes": [
                structural_load_result.get("digital_twin_update", {}).get("digital_twin_node", "structural_loads"),
                element_load_result.get("digital_twin_update", {}).get("digital_twin_node", "element_loads"),
                foundation_load_transfer_result.get("digital_twin_update", {}).get("digital_twin_node", "foundation_load_transfer"),
                foundation_design_result.get("digital_twin_update", {}).get("digital_twin_node", "foundation_design"),
                foundation_verification_result.get("digital_twin_update", {}).get("digital_twin_node", "foundation_verification"),
                structural_element_sizing_result.get("digital_twin_update", {}).get("digital_twin_node", "structural_element_sizing"),
                structural_reinforcement_result.get("digital_twin_update", {}).get("digital_twin_node", "structural_reinforcement"),
                structural_qaqc_result.get("digital_twin_update", {}).get("digital_twin_node", "structural_qaqc_review")
            ],
            "status": "DATA_OUTPUTS_VOORBEREID"
        }

    def build_folder_structure(self):
        return [
            "00_Projectgegevens",
            "01_Berekeningen",
            "02_Constructietekeningen",
            "03_CAD_DXF_DWG",
            "04_IFC_FreeCAD",
            "05_Digital_Twin_JSON",
            "06_QAQC",
            "07_Bronvermelding"
        ]

    def build_qa_qc_checks(self, source_statuses, document_outputs, data_outputs):
        checks = []

        for name, status in source_statuses.items():
            checks.append(
                {
                    "check": f"bron_{name}",
                    "status": "OK" if status != "ONTBREEKT" else "AANDACHT"
                }
            )

        for name, item in document_outputs.items():
            checks.append(
                {
                    "check": f"document_{name}",
                    "status": "OK" if item.get("status") != "ONTBREEKT" else "AANDACHT"
                }
            )

        checks.append(
            {
                "check": "digital_twin_data_outputs",
                "status": "OK" if data_outputs.get("status") == "DATA_OUTPUTS_VOORBEREID" else "AANDACHT"
            }
        )

        return checks

    def build_final_readiness(self, qa_qc_checks):
        attention_count = 0

        for check in qa_qc_checks:
            if check.get("status") == "AANDACHT":
                attention_count += 1

        if attention_count == 0:
            status = "CONCEPT_OUTPUT_PACKAGE_COMPLEET"
        else:
            status = "CONCEPT_OUTPUT_PACKAGE_MET_AANDACHTSPUNTEN"

        return {
            "status": status,
            "attention_count": attention_count,
            "ready_for_concept_export": True,
            "ready_for_definitive_submission": False
        }

    def build_warnings(self, qa_qc_checks, final_readiness):
        warnings = []

        for check in qa_qc_checks:
            if check.get("status") == "AANDACHT":
                warnings.append(f"Outputpakket aandachtspunt: {check.get('check')}.")

        if not final_readiness.get("ready_for_definitive_submission"):
            warnings.append("Definitieve indiening vereist nog normatieve berekening en constructeurcontrole.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in het constructieve outputpakket.")

        return warnings

    def safe_name(self, value):
        text = str(value).strip().lower()

        if not text:
            return "project"

        cleaned = []

        for char in text:
            if char.isalnum():
                cleaned.append(char)
            elif char in [" ", "-", "_"]:
                cleaned.append("_")

        result = "".join(cleaned)

        while "__" in result:
            result = result.replace("__", "_")

        return result.strip("_") or "project"

    def get_output_package_result(self):
        return self.output_package_result

    def create_output_package(self, *args, **kwargs):
        return self.create_structural_project_output_package(*args, **kwargs)

    def generate_structural_project_output_package(self, *args, **kwargs):
        return self.create_structural_project_output_package(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_project_output_package(*args, **kwargs)
"""


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

    module = importlib.import_module("baoees.structural_project_output_package_engine.main")
    engine_class = getattr(module, "StructuralProjectOutputPackageEngine")
    engine = engine_class()

    ok = {"status": "OK", "digital_twin_update": {"digital_twin_node": "test_node"}}

    result = engine.create_structural_project_output_package(
        project_result={"project_id": "test", "project_name": "Testproject"},
        structural_load_result=ok,
        element_load_result=ok,
        foundation_load_transfer_result=ok,
        foundation_design_result=ok,
        foundation_verification_result=ok,
        structural_element_sizing_result=ok,
        structural_reinforcement_result=ok,
        structural_calculation_report_result=ok,
        structural_drawing_package_result=ok,
        structural_cad_export_result=ok,
        structural_qaqc_result=ok
    )

    if result.get("status") != "STRUCTURAL_PROJECT_OUTPUT_PACKAGE_GEREED":
        raise RuntimeError("Structural Project Output Package Engine gaf geen correcte status terug.")

    if result.get("final_readiness", {}).get("ready_for_concept_export") is not True:
        raise RuntimeError("Structural Project Output Package Engine gaf geen concept-export vrij.")

    print("")
    print("STRUCTURAL_PROJECT_OUTPUT_PACKAGE_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Readiness: {result.get('final_readiness', {}).get('status')}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("STRUCTURAL_PROJECT_OUTPUT_PACKAGE_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/structural_project_output_package_engine/__init__.py")
    run_command("git add baoees/structural_project_output_package_engine/main.py")
    run_command("git add tools_create_structural_project_output_package_engine_v1.py")
    run_command('git commit -m "feat: add Structural Project Output Package Engine v1"')
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
