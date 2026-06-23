import json
from datetime import datetime
from pathlib import Path


class ProjectSelectorEngine:

    def __init__(self):
        self.selector_result = {}

    def select_project(self, project_id=None, index_path=None):
        if index_path is None:
            index_path = Path("configs/projects/project_index.json")
        else:
            index_path = Path(index_path)

        project_index = self.load_project_index(index_path)

        selected_project = self.find_selected_project(
            project_index=project_index,
            project_id=project_id
        )

        validation = self.validate_selected_project(selected_project)

        self.selector_result = {
            "engine": "ProjectSelectorEngine",
            "version": "1.0",
            "status": "PROJECT_SELECTIE_GEREED",
            "calculation_level": "projectbibliotheek en projectselectie",
            "index_path": str(index_path),
            "requested_project_id": project_id,
            "active_project_id": project_index.get("active_project_id"),
            "selected_project": selected_project,
            "selected_config_path": selected_project.get("config_path"),
            "available_projects": project_index.get("projects", []),
            "available_project_count": len(project_index.get("projects", [])),
            "validation": validation,
            "warnings": self.build_warnings(project_index, selected_project, validation),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Selector Engine v1.0 kiest een project uit een lokale JSON-projectindex. "
                "Later kan deze selectie worden gekoppeld aan het BAOEES startscherm, gebruikersprofielen, "
                "projectbibliotheek, uploadmap en cloudopslag."
            )
        }

        return self.selector_result

    def load_project_index(self, index_path):
        if not index_path.exists():
            return {
                "status": "PROJECT_INDEX_NIET_GEVONDEN",
                "active_project_id": "plutostraat",
                "projects": []
            }

        try:
            with open(index_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            data["status"] = "PROJECT_INDEX_GELADEN"
            return data

        except json.JSONDecodeError as error:
            return {
                "status": "PROJECT_INDEX_FOUT",
                "active_project_id": "plutostraat",
                "projects": [],
                "error": str(error)
            }

    def find_selected_project(self, project_index, project_id=None):
        projects = project_index.get("projects", [])

        if project_id is None:
            project_id = project_index.get("active_project_id")

        for project in projects:
            if project.get("project_id") == project_id:
                return project

        if projects:
            fallback_project = projects[0].copy()
            fallback_project["_fallback_reason"] = "gevraagd project niet gevonden; eerste project gebruikt"
            return fallback_project

        return {
            "project_id": "plutostraat",
            "project_name": "Plutostraat met BAOEES V3",
            "project_type": "Bouw",
            "location": "Plutostraat, Paramaribo",
            "country": "Suriname",
            "config_path": "configs/projects/plutostraat.json",
            "status": "fallback",
            "description": "Fallback projectconfiguratie."
        }

    def validate_selected_project(self, selected_project):
        required_fields = [
            "project_id",
            "project_name",
            "project_type",
            "location",
            "country",
            "config_path"
        ]

        missing_fields = []

        for field in required_fields:
            value = selected_project.get(field)
            if value is None or value == "":
                missing_fields.append(field)

        config_path = selected_project.get("config_path", "")
        config_exists = Path(config_path).exists() if config_path else False

        if missing_fields:
            status = "PROJECT_SELECTIE_ONVOLLEDIG"
        elif not config_exists:
            status = "PROJECT_CONFIG_BESTAND_NIET_GEVONDEN"
        else:
            status = "PROJECT_SELECTIE_VALID"

        return {
            "status": status,
            "required_fields": required_fields,
            "missing_fields": missing_fields,
            "config_path": config_path,
            "config_exists": config_exists,
            "is_valid": len(missing_fields) == 0 and config_exists
        }

    def build_warnings(self, project_index, selected_project, validation):
        warnings = []

        if project_index.get("status") != "PROJECT_INDEX_GELADEN":
            warnings.append("Projectindex kon niet correct worden geladen.")

        if validation.get("status") == "PROJECT_CONFIG_BESTAND_NIET_GEVONDEN":
            warnings.append(
                "Het gekozen project heeft nog geen bestaand JSON-configbestand."
            )

        if validation.get("status") == "PROJECT_SELECTIE_ONVOLLEDIG":
            warnings.append(
                "Het gekozen project mist verplichte velden in de projectindex."
            )

        if selected_project.get("_fallback_reason"):
            warnings.append(selected_project.get("_fallback_reason"))

        if not warnings:
            warnings.append("Geen kritieke projectselectie-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_SELECTOR_ADVIES",
            "advice": (
                "Gebruik deze engine om BAOEES niet meer op één vast project te laten draaien, "
                "maar op een gekozen project uit de projectbibliotheek."
            ),
            "next_steps": [
                "ProjectSelectorEngine koppelen aan BAOEES Core",
                "config_path doorgeven aan ProjectConfigEngine",
                "Moskee Bunschoten JSON-config toevoegen",
                "Bruynzeel Waterfront JSON-config toevoegen",
                "projectkeuze zichtbaar maken in startscherm",
                "projectbibliotheek uitbreiden met status, datum, opdrachtgever en revisie"
            ]
        }

    def get_selector_result(self):
        return self.selector_result

    def run(self):
        print("Project Selector / Project Library Engine actief")