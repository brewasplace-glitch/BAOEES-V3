from datetime import datetime
from pathlib import Path


class ProjectStorageEngine:

    def __init__(self):
        self.storage_result = {}

    def prepare_project_storage(
        self,
        project_result=None,
        selector_result=None,
        config_result=None
    ):
        project_result = project_result or {}
        selector_result = selector_result or {}
        config_result = config_result or {}

        project_id = self.resolve_project_id(project_result, selector_result)
        project_name = project_result.get("project_name", "Onbekend project")

        base_output_dir = Path("outputs/projects")
        project_output_dir = base_output_dir / project_id

        folder_structure = self.build_folder_structure(project_output_dir)
        created_folders = self.create_folders(folder_structure)

        self.storage_result = {
            "engine": "ProjectStorageEngine",
            "version": "1.0",
            "status": "PROJECT_STORAGE_GEREED",
            "calculation_level": "projectspecifieke outputmap",
            "project_id": project_id,
            "project_name": project_name,
            "base_output_dir": str(base_output_dir),
            "project_output_dir": str(project_output_dir),
            "folder_structure": folder_structure,
            "created_folders": created_folders,
            "storage_manifest": self.build_storage_manifest(
                project_id=project_id,
                project_name=project_name,
                project_output_dir=project_output_dir,
                config_result=config_result
            ),
            "warnings": self.build_warnings(created_folders),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Storage Engine v1.0 maakt alleen de projectmapstructuur. "
                "In vervolgstappen kunnen rapporten, tekeningen, logs, Digital Twin-data, "
                "bronvermelding en ZIP-bestanden fysiek naar deze mappen worden geschreven."
            )
        }

        return self.storage_result

    def resolve_project_id(self, project_result, selector_result):
        selected_project = selector_result.get("selected_project", {})
        project_id = selected_project.get("project_id")

        if not project_id:
            project_id = project_result.get("selected_project_id")

        if not project_id:
            project_name = project_result.get("project_name", "unknown_project")
            project_id = (
                project_name.lower()
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
                .replace("-", "_")
            )

        return project_id

    def build_folder_structure(self, project_output_dir):
        return {
            "root": str(project_output_dir),
            "reports": str(project_output_dir / "01_reports"),
            "drawings": str(project_output_dir / "02_drawings"),
            "cad": str(project_output_dir / "03_cad"),
            "calculations": str(project_output_dir / "04_calculations"),
            "permits": str(project_output_dir / "05_permits"),
            "sources": str(project_output_dir / "06_sources"),
            "digital_twin": str(project_output_dir / "07_digital_twin"),
            "runtime_logs": str(project_output_dir / "08_runtime_logs"),
            "exports": str(project_output_dir / "09_exports"),
            "zip": str(project_output_dir / "10_zip")
        }

    def create_folders(self, folder_structure):
        created = []

        for key, folder_path in folder_structure.items():
            path = Path(folder_path)
            path.mkdir(parents=True, exist_ok=True)

            created.append({
                "folder_key": key,
                "path": str(path),
                "exists": path.exists()
            })

        return created

    def build_storage_manifest(
        self,
        project_id,
        project_name,
        project_output_dir,
        config_result
    ):
        return {
            "status": "PROJECT_STORAGE_MANIFEST_CONCEPT",
            "project_id": project_id,
            "project_name": project_name,
            "project_output_dir": str(project_output_dir),
            "config_status": config_result.get("status", "ONBEKEND"),
            "planned_files": [
                "project_config.json",
                "digital_twin.json",
                "runtime_log.json",
                "source_register.json",
                "qa_qc_report.json",
                "project_report.pdf",
                "project_report.docx",
                "drawings_overview.pdf",
                "cad_exports.zip",
                "project_export.zip"
            ]
        }

    def build_warnings(self, created_folders):
        warnings = []

        for folder in created_folders:
            if not folder.get("exists"):
                warnings.append(
                    f"Map kon niet worden aangemaakt: {folder.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke opslagwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_STORAGE_ADVIES",
            "advice": (
                "Gebruik deze engine als centrale opslaglaag voor alle projectoutput. "
                "Elke projectanalyse krijgt hiermee een vaste mapstructuur, zodat rapporten, "
                "tekeningen, berekeningen, bronbestanden en exports niet door elkaar lopen."
            ),
            "next_steps": [
                "ProjectStorageEngine koppelen aan BAOEES Core",
                "storage_result toevoegen aan Digital Twin",
                "rapportage-export naar projectmap laten schrijven",
                "Digital Twin als JSON opslaan",
                "STEE bronregister fysiek opslaan",
                "Project ZIP Engine koppelen aan project_output_dir"
            ]
        }

    def get_storage_result(self):
        return self.storage_result

    def run(self):
        print("Project Storage / Output Folder Engine actief")