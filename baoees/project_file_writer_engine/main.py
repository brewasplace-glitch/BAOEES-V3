import json
from datetime import datetime
from pathlib import Path


class ProjectFileWriterEngine:

    def __init__(self):
        self.file_writer_result = {}

    def write_project_files(
        self,
        project_result=None,
        storage_result=None,
        config_result=None,
        selector_result=None,
        digital_twin_data=None,
        stee_result=None,
        runtime_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        config_result = config_result or {}
        selector_result = selector_result or {}
        digital_twin_data = digital_twin_data or {}
        stee_result = stee_result or {}
        runtime_result = runtime_result or {}
        validation_result = validation_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(storage_result.get("project_output_dir", "outputs/projects/unknown_project"))

        files_to_write = {
            "project_config": {
                "path": project_output_dir / "project_config.json",
                "data": config_result
            },
            "project_selector": {
                "path": project_output_dir / "project_selector.json",
                "data": selector_result
            },
            "digital_twin": {
                "path": Path(folder_structure.get("digital_twin", project_output_dir / "07_digital_twin")) / "digital_twin.json",
                "data": digital_twin_data
            },
            "source_register": {
                "path": Path(folder_structure.get("sources", project_output_dir / "06_sources")) / "source_register.json",
                "data": stee_result
            },
            "runtime_log": {
                "path": Path(folder_structure.get("runtime_logs", project_output_dir / "08_runtime_logs")) / "runtime_log.json",
                "data": runtime_result
            },
            "qa_qc_report": {
                "path": Path(folder_structure.get("calculations", project_output_dir / "04_calculations")) / "qa_qc_report.json",
                "data": validation_result
            },
            "project_summary": {
                "path": project_output_dir / "project_summary.json",
                "data": self.build_project_summary(
                    project_result=project_result,
                    storage_result=storage_result,
                    config_result=config_result,
                    selector_result=selector_result,
                    runtime_result=runtime_result,
                    validation_result=validation_result
                )
            }
        }

        written_files = []

        for file_key, file_info in files_to_write.items():
            written_files.append(
                self.write_json_file(
                    file_key=file_key,
                    file_path=file_info["path"],
                    data=file_info["data"]
                )
            )

        self.file_writer_result = {
            "engine": "ProjectFileWriterEngine",
            "version": "1.0",
            "status": "PROJECT_FILES_OPGESLAGEN",
            "calculation_level": "JSON projectoutput export",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_id": storage_result.get("project_id", "unknown_project"),
            "project_output_dir": str(project_output_dir),
            "written_files": written_files,
            "written_file_count": len(written_files),
            "warnings": self.build_warnings(written_files),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project File Writer Engine v1.0 schrijft projectdata als JSON-bestanden. "
                "PDF, DOCX, DXF, IFC en ZIP-bestanden worden in latere engines of vervolgstappen "
                "fysiek gegenereerd."
            )
        }

        return self.file_writer_result

    def write_json_file(self, file_key, file_path, data):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False, default=str)

            return {
                "file_key": file_key,
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists()
            }

        except Exception as error:
            return {
                "file_key": file_key,
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "error": str(error)
            }

    def build_project_summary(
        self,
        project_result,
        storage_result,
        config_result,
        selector_result,
        runtime_result,
        validation_result
    ):
        return {
            "status": "PROJECT_SUMMARY_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_id": storage_result.get("project_id", "unknown_project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "project_type": project_result.get("project_type", "Onbekend"),
            "runtime_mode": project_result.get("runtime_mode", "onbekend"),
            "selected_project": selector_result.get("selected_project", {}),
            "config_status": config_result.get("status", "ONBEKEND"),
            "runtime_status": runtime_result.get("status", "ONBEKEND"),
            "qa_qc_status": validation_result.get("status", "ONBEKEND"),
            "project_output_dir": storage_result.get("project_output_dir"),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

    def build_warnings(self, written_files):
        warnings = []

        for file_info in written_files:
            if file_info.get("status") != "OPGESLAGEN":
                warnings.append(
                    f"Bestand niet opgeslagen: {file_info.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke bestandsopslag-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_FILE_WRITER_ADVIES",
            "advice": (
                "Gebruik deze engine om alle belangrijke BAOEES-resultaten fysiek in de "
                "projectmap op te slaan. Dit maakt de projectmap controleerbaar, exporteerbaar "
                "en geschikt voor latere ZIP- en rapportagegeneratie."
            ),
            "next_steps": [
                "ProjectFileWriterEngine koppelen aan BAOEES Core",
                "project_file_writer_result toevoegen aan Digital Twin",
                "PDF/DOCX generator koppelen aan 01_reports",
                "DXF/DWG generator koppelen aan 03_cad",
                "Project ZIP Engine koppelen aan opgeslagen projectmap",
                "automatische bestandscontrole toevoegen"
            ]
        }

    def get_file_writer_result(self):
        return self.file_writer_result

    def run(self):
        print("Project File Writer / JSON Export Engine actief")