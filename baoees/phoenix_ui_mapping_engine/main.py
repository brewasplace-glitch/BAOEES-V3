from datetime import datetime


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
