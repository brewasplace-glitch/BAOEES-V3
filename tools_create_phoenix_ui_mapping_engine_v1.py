from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/phoenix_ui_mapping_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import PhoenixUIMappingEngine\n"

MAIN_CONTENT = """from datetime import datetime


class PhoenixUIMappingEngine:

    def __init__(self):
        self.ui_mapping_result = {}

    def create_phoenix_ui_mapping(
        self,
        project_result=None,
        phoenix_bridge_result=None,
        structural_project_output_package_result=None,
        structural_qaqc_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        phoenix_bridge_result = phoenix_bridge_result or {}
        structural_project_output_package_result = structural_project_output_package_result or {}
        structural_qaqc_result = structural_qaqc_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        dashboard = {
            "dashboard_id": "phoenix_home_dashboard",
            "status": "DASHBOARD_MAPPING_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "title": "Phoenix Project Dashboard",
            "default_mode": "fullscreen",
            "layout": "tiles_plus_status_panel",
            "primary_button": "START PROJECTANALYSE"
        }

        tiles = self.build_tiles(
            phoenix_bridge_result,
            structural_project_output_package_result,
            structural_qaqc_result
        )

        actions = [
            {
                "action_id": "start_project_analysis",
                "label": "START PROJECTANALYSE",
                "backend_command": "python run_baoees_v3.py",
                "mode": "fully_autonomous"
            },
            {
                "action_id": "run_qaqc",
                "label": "Voer QA/QC uit",
                "backend_target": "StructuralQAQCEngine"
            },
            {
                "action_id": "generate_output_package",
                "label": "Genereer outputpakket",
                "backend_target": "StructuralProjectOutputPackageEngine"
            },
            {
                "action_id": "export_project_zip",
                "label": "Exporteer project-ZIP",
                "backend_target": "ProjectExportEngine"
            }
        ]

        navigation = {
            "status": "NAVIGATIE_GEREED",
            "sections": [
                "Home",
                "Project",
                "Engines",
                "Digital Twin",
                "Rapporten",
                "Tekeningen",
                "CAD/BIM",
                "QA/QC",
                "Bronnen",
                "Instellingen"
            ]
        }

        status_panel = self.build_status_panel(
            phoenix_bridge_result,
            structural_project_output_package_result,
            structural_qaqc_result
        )

        output_panel = self.build_output_panel(structural_project_output_package_result)
        readiness = self.build_readiness(tiles, actions, phoenix_bridge_result)

        self.ui_mapping_result = {
            "engine": "PhoenixUIMappingEngine",
            "version": "1.0",
            "status": "PHOENIX_UI_MAPPING_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "dashboard": dashboard,
            "tiles": tiles,
            "actions": actions,
            "navigation": navigation,
            "status_panel": status_panel,
            "output_panel": output_panel,
            "readiness": readiness,
            "digital_twin_update": {
                "digital_twin_node": "phoenix_ui_mapping",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "dashboard": dashboard,
                    "tiles": tiles,
                    "actions": actions,
                    "navigation": navigation,
                    "status_panel": status_panel,
                    "output_panel": output_panel,
                    "readiness": readiness
                }
            },
            "warnings": self.build_warnings(readiness),
            "recommendation": {
                "status": "PHOENIX_UI_MAPPING_ADVIES",
                "advice": (
                    "Gebruik deze mapping als basis voor het Phoenix hoofdscherm. "
                    "Phoenix toont hiermee de BAOEES/Wizard engine-uitkomsten als dashboardtegels, "
                    "acties en downloadpanelen."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.ui_mapping_result

    def build_tiles(
        self,
        phoenix_bridge_result,
        structural_project_output_package_result,
        structural_qaqc_result
    ):
        bridge_status = phoenix_bridge_result.get("status", "ONTBREEKT")
        output_status = structural_project_output_package_result.get("status", "ONTBREEKT")
        qaqc_status = structural_qaqc_result.get("status", "ONTBREEKT")

        return [
            {"tile_id": "project_intake", "title": "Projectinvoer", "status": "ACTIEF"},
            {"tile_id": "phoenix_bridge", "title": "Phoenix BAOEES Bridge", "status": bridge_status},
            {"tile_id": "structural_chain", "title": "Constructieve keten", "status": "BESCHIKBAAR"},
            {"tile_id": "qaqc", "title": "QA/QC", "status": qaqc_status},
            {"tile_id": "output_package", "title": "Outputpakket", "status": output_status},
            {"tile_id": "digital_twin", "title": "Digital Twin", "status": "KOPPELBAAR"},
            {"tile_id": "exports", "title": "Downloads en Export", "status": "VOORBEREID"},
            {"tile_id": "source_traceability", "title": "Bronvermelding", "status": "VOORBEREID"}
        ]

    def build_status_panel(
        self,
        phoenix_bridge_result,
        structural_project_output_package_result,
        structural_qaqc_result
    ):
        output_readiness = structural_project_output_package_result.get("final_readiness", {})
        bridge_readiness = phoenix_bridge_result.get("bridge_readiness", {})
        qaqc_approval = structural_qaqc_result.get("approval_status", {})

        return {
            "status": "STATUS_PANEL_GEREED",
            "bridge": bridge_readiness.get("status", phoenix_bridge_result.get("status", "ONTBREEKT")),
            "output_package": output_readiness.get("status", structural_project_output_package_result.get("status", "ONTBREEKT")),
            "qaqc": qaqc_approval.get("status", structural_qaqc_result.get("status", "ONTBREEKT")),
            "overall": "CONCEPT_DASHBOARD_GEREED"
        }

    def build_output_panel(self, structural_project_output_package_result):
        return {
            "status": "OUTPUT_PANEL_GEREED",
            "document_outputs": structural_project_output_package_result.get("document_outputs", {}),
            "folder_structure": structural_project_output_package_result.get("folder_structure", []),
            "download_buttons": [
                "Download PDF rapport",
                "Download DOCX rapport",
                "Download tekeningenpakket",
                "Download CAD/BIM export",
                "Download project-ZIP",
                "Download bronvermelding"
            ]
        }

    def build_readiness(self, tiles, actions, phoenix_bridge_result):
        attention = []

        if not tiles:
            attention.append("tiles_ontbreken")

        if not actions:
            attention.append("actions_ontbreken")

        if phoenix_bridge_result.get("status", "ONTBREEKT") == "ONTBREEKT":
            attention.append("phoenix_bridge_niet_gekoppeld")

        if attention:
            status = "PHOENIX_UI_MAPPING_MET_AANDACHTSPUNTEN"
        else:
            status = "PHOENIX_UI_MAPPING_CONCEPT_GEREED"

        return {
            "status": status,
            "attention_points": attention,
            "ready_for_frontend_implementation": True,
            "ready_for_production": False
        }

    def build_warnings(self, readiness):
        warnings = []

        for item in readiness.get("attention_points", []):
            warnings.append(f"Phoenix UI aandachtspunt: {item}.")

        if readiness.get("ready_for_production") is False:
            warnings.append(
                "Productiegebruik vereist nog echte frontend-componenten, routing en API-koppeling."
            )

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de Phoenix UI Mapping.")

        return warnings

    def get_ui_mapping_result(self):
        return self.ui_mapping_result

    def create_ui_mapping(self, *args, **kwargs):
        return self.create_phoenix_ui_mapping(*args, **kwargs)

    def generate_phoenix_ui_mapping(self, *args, **kwargs):
        return self.create_phoenix_ui_mapping(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_phoenix_ui_mapping(*args, **kwargs)
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

    module = importlib.import_module("baoees.phoenix_ui_mapping_engine.main")
    engine_class = getattr(module, "PhoenixUIMappingEngine")
    engine = engine_class()

    result = engine.create_phoenix_ui_mapping(
        project_result={"project_id": "test", "project_name": "Testproject"},
        phoenix_bridge_result={
            "status": "PHOENIX_BRIDGE_PACKAGE_GEREED",
            "bridge_readiness": {"status": "PHOENIX_BRIDGE_CONCEPT_GEREED"}
        },
        structural_project_output_package_result={
            "status": "STRUCTURAL_PROJECT_OUTPUT_PACKAGE_GEREED",
            "final_readiness": {"status": "CONCEPT_OUTPUT_PACKAGE_COMPLEET"}
        },
        structural_qaqc_result={
            "status": "STRUCTURAL_QAQC_REVIEW_GEREED",
            "approval_status": {"status": "CONCEPT_KETEN_QAQC_OK"}
        }
    )

    if result.get("status") != "PHOENIX_UI_MAPPING_GEREED":
        raise RuntimeError("Phoenix UI Mapping Engine gaf geen correcte status terug.")

    if len(result.get("tiles", [])) < 8:
        raise RuntimeError("Phoenix UI Mapping Engine genereerde te weinig dashboardtegels.")

    print("")
    print("PHOENIX_UI_MAPPING_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Aantal tegels: {len(result.get('tiles', []))}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("PHOENIX_UI_MAPPING_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/phoenix_ui_mapping_engine/__init__.py")
    run_command("git add baoees/phoenix_ui_mapping_engine/main.py")
    run_command("git add tools_create_phoenix_ui_mapping_engine_v1.py")
    run_command('git commit -m "feat: add Phoenix UI Mapping Engine v1"')
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
