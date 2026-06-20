"""
BAOEES Project Export Engine v1.0

Doel:
- projectdata exporteren
- Digital Twin exporteren
- rapportstructuur exporteren
- bronregister exporteren
- exportmap voor project aanmaken
"""

import json
from datetime import datetime
from pathlib import Path


class ProjectExportEngine:

    def __init__(self, export_root="exports"):
        self.export_root = Path(export_root)
        self.export_result = {}

    def create_project_export(
        self,
        project_result=None,
        digital_twin_data=None,
        reporting_result=None,
        stee_result=None
    ):
        project_result = project_result or {}
        digital_twin_data = digital_twin_data or {}
        reporting_result = reporting_result or {}
        stee_result = stee_result or {}

        project_name = project_result.get("project_name", "onbekend_project")
        safe_project_name = self.make_safe_name(project_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_folder = self.export_root / f"{safe_project_name}_{timestamp}"
        export_folder.mkdir(parents=True, exist_ok=True)

        files = []

        files.append(
            self.write_json(
                export_folder / "project_summary.json",
                project_result
            )
        )

        files.append(
            self.write_json(
                export_folder / "digital_twin_export.json",
                digital_twin_data
            )
        )

        files.append(
            self.write_json(
                export_folder / "report_structure.json",
                reporting_result
            )
        )

        files.append(
            self.write_json(
                export_folder / "source_register.json",
                stee_result
            )
        )

        self.export_result = {
            "engine": "ProjectExportEngine",
            "status": "PROJECT_EXPORT_GEREED",
            "export_folder": str(export_folder),
            "exported_files": files,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "next_steps": [
                "PDF-export toevoegen",
                "DOCX-export toevoegen",
                "tekeningenmap toevoegen",
                "berekeningenmap toevoegen",
                "project-ZIP genereren"
            ]
        }

        return self.export_result

    def write_json(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        return {
            "file": str(file_path),
            "status": "AANGEMAAKT"
        }

    def make_safe_name(self, name):
        safe = name.lower()
        safe = safe.replace(" ", "_")
        safe = safe.replace("/", "_")
        safe = safe.replace("\\", "_")
        safe = safe.replace(":", "_")
        safe = safe.replace("*", "_")
        safe = safe.replace("?", "_")
        safe = safe.replace('"', "_")
        safe = safe.replace("<", "_")
        safe = safe.replace(">", "_")
        safe = safe.replace("|", "_")
        return safe

    def get_export_result(self):
        return self.export_result

    def run(self):
        print("Project Export Engine actief")