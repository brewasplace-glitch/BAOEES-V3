import os
import zipfile
from datetime import datetime
from pathlib import Path


class ProjectZipEngine:

    def __init__(self):
        self.zip_result = {}

    def create_project_zip(
        self,
        export_result=None,
        storage_result=None,
        file_writer_result=None
    ):
        export_result = export_result or {}
        storage_result = storage_result or {}
        file_writer_result = file_writer_result or {}

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = storage_result.get("project_name", "Onbekend project")

        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                f"outputs/projects/{project_id}"
            )
        )

        folder_structure = storage_result.get("folder_structure", {})
        zip_folder = Path(
            folder_structure.get(
                "zip",
                project_output_dir / "10_zip"
            )
        )

        zip_folder.mkdir(parents=True, exist_ok=True)

        zip_file_name = f"{project_id}_project_export.zip"
        zip_file_path = zip_folder / zip_file_name

        zipped_files = self.create_zip_file(
            project_output_dir=project_output_dir,
            zip_file_path=zip_file_path
        )

        self.zip_result = {
            "engine": "ProjectZipEngine",
            "version": "1.1",
            "status": "PROJECT_ZIP_OPGESLAGEN",
            "calculation_level": "echte projectmap ZIP-export",
            "project_id": project_id,
            "project_name": project_name,
            "project_output_dir": str(project_output_dir),
            "zip_folder": str(zip_folder),
            "zip_file_name": zip_file_name,
            "zip_file_path": str(zip_file_path),
            "zip_exists": zip_file_path.exists(),
            "zip_size_bytes": self.get_file_size(zip_file_path),
            "zipped_files": zipped_files,
            "zipped_file_count": len(zipped_files),
            "file_writer_status": file_writer_result.get("status", "ONBEKEND"),
            "export_status": export_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(
                zip_file_path=zip_file_path,
                zipped_files=zipped_files
            ),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project ZIP Engine v1.1 maakt een echte ZIP-export van de projectmap. "
                "Alle aanwezige bestanden in de projectmap worden meegenomen, behalve bestaande ZIP-bestanden "
                "in de 10_zip-map om dubbele nesting te voorkomen."
            )
        }

        return self.zip_result

    def create_zip_file(self, project_output_dir, zip_file_path):
        project_output_dir = Path(project_output_dir)
        zip_file_path = Path(zip_file_path)

        zipped_files = []

        if not project_output_dir.exists():
            return zipped_files

        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(project_output_dir):
                root_path = Path(root)

                for file_name in files:
                    file_path = root_path / file_name

                    if file_path == zip_file_path:
                        continue

                    if file_path.suffix.lower() == ".zip" and "10_zip" in str(file_path):
                        continue

                    archive_name = file_path.relative_to(project_output_dir)

                    zip_file.write(file_path, archive_name)

                    zipped_files.append({
                        "source_path": str(file_path),
                        "archive_name": str(archive_name),
                        "size_bytes": self.get_file_size(file_path)
                    })

        return zipped_files

    def get_file_size(self, file_path):
        file_path = Path(file_path)

        if not file_path.exists():
            return 0

        return file_path.stat().st_size

    def build_warnings(self, zip_file_path, zipped_files):
        warnings = []

        if not Path(zip_file_path).exists():
            warnings.append("ZIP-bestand is niet aangemaakt.")

        if len(zipped_files) == 0:
            warnings.append("Er zijn geen bestanden toegevoegd aan de ZIP-export.")

        if not warnings:
            warnings.append("Geen kritieke ZIP-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_ZIP_ADVIES",
            "advice": (
                "Gebruik deze ZIP-export als downloadbaar projectdossier. "
                "De volgende stap is om ook echte PDF/DOCX/DXF-bestanden en rapportages "
                "naar de projectmap te schrijven, zodat de ZIP een volledig projectpakket wordt."
            ),
            "next_steps": [
                "Project ZIP Engine koppelen aan storage_result",
                "ZIP-pad tonen in project_summary.json",
                "PDF/DOCX-rapporten fysiek genereren",
                "CAD/DXF-bestanden fysiek genereren",
                "ZIP-export opnemen in startscherm als downloadknop",
                "controle toevoegen of alle verplichte projectbestanden aanwezig zijn"
            ]
        }

    def get_zip_result(self):
        return self.zip_result

    def run(self):
        print("Project ZIP Engine actief")