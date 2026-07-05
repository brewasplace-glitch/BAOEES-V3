from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/phoenix_bridge_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import PhoenixBridgeEngine\n"

MAIN_CONTENT = '''from datetime import datetime


class PhoenixBridgeEngine:

    def __init__(self):
        self.bridge_result = {}

    def create_phoenix_bridge_package(
        self,
        project_result=None,
        structural_project_output_package_result=None,
        structural_qaqc_result=None,
        digital_twin_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_project_output_package_result = structural_project_output_package_result or {}
        structural_qaqc_result = structural_qaqc_result or {}
        digital_twin_result = digital_twin_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        capabilities = self.build_capability_manifest()
        intake_contract = self.build_intake_contract()
        workflow_contract = self.build_workflow_contract()
        output_contract = self.build_output_contract(structural_project_output_package_result)
        digital_twin_contract = self.build_digital_twin_contract(digital_twin_result)
        automation_contract = self.build_automation_contract()
        bridge_readiness = self.build_bridge_readiness(
            capabilities,
            output_contract,
            structural_project_output_package_result,
            structural_qaqc_result
        )

        self.bridge_result = {
            "engine": "PhoenixBridgeEngine",
            "version": "1.0",
            "status": "PHOENIX_BRIDGE_PACKAGE_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "bridge_type": "Phoenix hoofdplatform naar BAOEES/Wizard engine-laag",
            "capability_manifest": capabilities,
            "intake_contract": intake_contract,
            "workflow_contract": workflow_contract,
            "output_contract": output_contract,
            "digital_twin_contract": digital_twin_contract,
            "automation_contract": automation_contract,
            "bridge_readiness": bridge_readiness,
            "digital_twin_update": {
                "digital_twin_node": "phoenix_bridge",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "capability_manifest": capabilities,
                    "workflow_contract": workflow_contract,
                    "output_contract": output_contract,
                    "bridge_readiness": bridge_readiness
                }
            },
            "warnings": self.build_warnings(bridge_readiness),
            "recommendation": {
                "status": "PHOENIX_BRIDGE_ADVIES",
                "advice": (
                    "Gebruik Phoenix als hoofdscherm en workflowlaag. "
                    "Laat Phoenix de bestaande BAOEES/Wizard engines aanroepen als backend, "
                    "zodat bestaand werk niet verloren gaat."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.bridge_result

    def build_capability_manifest(self):
        return {
            "status": "CAPABILITIES_GEREED",
            "platform_role": "frontend_orchestrator",
            "backend_role": "baoees_wizard_engine_layer",
            "available_domains": [
                "project_intake",
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
                "structural_cad_export",
                "structural_qaqc",
                "structural_project_output_package"
            ],
            "supported_outputs": [
                "PDF",
                "DOCX",
                "DXF",
                "DWG",
                "IFC",
                "FreeCAD",
                "JSON",
                "Digital Twin data"
            ],
            "automation_modes": [
                "assistant",
                "semi_autonomous",
                "fully_autonomous"
            ]
        }

    def build_intake_contract(self):
        return {
            "status": "INTAKE_CONTRACT_GEREED",
            "required_fields": [
                "project_name",
                "location",
                "project_type",
                "user_goal"
            ],
            "optional_fields": [
                "drawings",
                "images",
                "pdf_reports",
                "soil_data",
                "loads",
                "foundation_preference",
                "output_formats",
                "automation_mode"
            ],
            "phoenix_input_methods": [
                "form",
                "voice",
                "file_upload",
                "map_selection",
                "chat_instruction"
            ]
        }

    def build_workflow_contract(self):
        return {
            "status": "WORKFLOW_CONTRACT_GEREED",
            "phoenix_start_action": "START_PROJECTANALYSE",
            "backend_entrypoint": "run_baoees_v3.py",
            "chain_policy": "Phoenix stuurt de workflow aan, BAOEES/Wizard voert engines uit.",
            "default_sequence": [
                "intake",
                "assumption_completion",
                "engine_chain",
                "qaqc",
                "output_package",
                "digital_twin_update",
                "project_export"
            ]
        }

    def build_output_contract(self, structural_project_output_package_result):
        package_status = structural_project_output_package_result.get("status", "ONTBREEKT")
        readiness = structural_project_output_package_result.get("final_readiness", {})

        return {
            "status": "OUTPUT_CONTRACT_GEREED",
            "source_package_status": package_status,
            "readiness": readiness,
            "phoenix_output_tiles": [
                "project_dashboard",
                "constructieve_samenvatting",
                "berekeningsrapport",
                "tekeningenpakket",
                "cad_export",
                "qaqc",
                "digital_twin",
                "bronvermelding"
            ],
            "download_package_policy": "Projectoutput moet als centrale ZIP beschikbaar worden gemaakt."
        }

    def build_digital_twin_contract(self, digital_twin_result):
        return {
            "status": "DIGITAL_TWIN_CONTRACT_GEREED",
            "source_status": digital_twin_result.get("status", "OPTIONEEL"),
            "sync_direction": "BAOEES_Wizard_to_Phoenix",
            "nodes_to_surface_in_phoenix": [
                "project",
                "building_technical",
                "structural_chain",
                "foundation",
                "reinforcement",
                "drawings",
                "cad_export",
                "qaqc",
                "output_package"
            ]
        }

    def build_automation_contract(self):
        return {
            "status": "AUTOMATION_CONTRACT_GEREED",
            "default_mode": "fully_autonomous",
            "human_checkpoints": [
                "project_start_confirmation",
                "assumption_review",
                "concept_output_review",
                "definitive_engineer_approval"
            ],
            "automatic_steps": [
                "engine_audit",
                "engine_execution",
                "qaqc_review",
                "output_package_generation",
                "git_commit_push",
                "project_status_report"
            ]
        }

    def build_bridge_readiness(
        self,
        capabilities,
        output_contract,
        structural_project_output_package_result,
        structural_qaqc_result
    ):
        attention = []

        if capabilities.get("status") != "CAPABILITIES_GEREED":
            attention.append("capability_manifest")

        if output_contract.get("source_package_status") == "ONTBREEKT":
            attention.append("structural_project_output_package")

        if structural_qaqc_result and structural_qaqc_result.get("status") == "ONTBREEKT":
            attention.append("structural_qaqc")

        if attention:
            status = "PHOENIX_BRIDGE_CONCEPT_MET_AANDACHTSPUNTEN"
        else:
            status = "PHOENIX_BRIDGE_CONCEPT_GEREED"

        return {
            "status": status,
            "attention_points": attention,
            "ready_for_phoenix_ui_mapping": True,
            "ready_for_production": False
        }

    def build_warnings(self, bridge_readiness):
        warnings = []

        for item in bridge_readiness.get("attention_points", []):
            warnings.append(f"Phoenix Bridge aandachtspunt: {item}.")

        if bridge_readiness.get("ready_for_production") is False:
            warnings.append(
                "Productiegebruik vereist nog echte Phoenix UI-koppeling, API-laag en eindtest."
            )

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de Phoenix Bridge conceptkoppeling.")

        return warnings

    def get_bridge_result(self):
        return self.bridge_result

    def create_bridge_package(self, *args, **kwargs):
        return self.create_phoenix_bridge_package(*args, **kwargs)

    def generate_phoenix_bridge_package(self, *args, **kwargs):
        return self.create_phoenix_bridge_package(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_phoenix_bridge_package(*args, **kwargs)
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

    module = importlib.import_module("baoees.phoenix_bridge_engine.main")
    engine_class = getattr(module, "PhoenixBridgeEngine")
    engine = engine_class()

    result = engine.create_phoenix_bridge_package(
        project_result={
            "project_id": "test",
            "project_name": "Testproject"
        },
        structural_project_output_package_result={
            "status": "STRUCTURAL_PROJECT_OUTPUT_PACKAGE_GEREED",
            "final_readiness": {
                "status": "CONCEPT_OUTPUT_PACKAGE_COMPLEET"
            }
        },
        structural_qaqc_result={
            "status": "STRUCTURAL_QAQC_REVIEW_GEREED"
        }
    )

    if result.get("status") != "PHOENIX_BRIDGE_PACKAGE_GEREED":
        raise RuntimeError("Phoenix Bridge Engine gaf geen correcte status terug.")

    if result.get("bridge_readiness", {}).get("ready_for_phoenix_ui_mapping") is not True:
        raise RuntimeError("Phoenix Bridge Engine gaf UI-mapping niet vrij.")

    print("")
    print("PHOENIX_BRIDGE_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Readiness: {result.get('bridge_readiness', {}).get('status')}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("PHOENIX_BRIDGE_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/phoenix_bridge_engine/__init__.py")
    run_command("git add baoees/phoenix_bridge_engine/main.py")
    run_command("git add tools_create_phoenix_bridge_engine_v1.py")
    run_command('git commit -m "feat: add Phoenix Bridge Engine v1"')
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
