"""
BAOEES Project ZIP Engine v1.0

Doel:
- projectexportmap comprimeren tot één ZIP-bestand
- ZIP-pad registreren
- latere download/export voorbereiden
"""

import shutil
from datetime import datetime
from pathlib import Path


class ProjectZipEngine:

    def __init__(self):
        self.zip_result = {}

    def create_project_zip(self, export_result=None):
        export_result = export_result or {}

        export_folder = export_result.get("export_folder")

        if not export_folder:
            self.zip_result = {
                "engine": "ProjectZipEngine",
                "status": "ZIP_EXPORT_MISLUKT",
                "reason": "Geen export_folder gevonden in export_result."
            }
            return self.zip_result

        export_folder_path = Path(export_folder)

        if not export_folder_path.exists():
            self.zip_result = {
                "engine": "ProjectZipEngine",
                "status": "ZIP_EXPORT_MISLUKT",
                "reason": f"Exportmap bestaat niet: {export_folder_path}"
            }
            return self.zip_result

        zip_base_path = export_folder_path
        zip_file_path = Path(f"{zip_base_path}.zip")

        shutil.make_archive(
            base_name=str(zip_base_path),
            format="zip",
            root_dir=str(export_folder_path)
        )

        self.zip_result = {
            "engine": "ProjectZipEngine",
            "status": "PROJECT_ZIP_GEREED",
            "zip_file": str(zip_file_path),
            "source_export_folder": str(export_folder_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": "Projectexport is succesvol ingepakt als ZIP-bestand."
        }

        return self.zip_result

    def get_zip_result(self):
        return self.zip_result

    def run(self):
        print("Project ZIP Engine actief")