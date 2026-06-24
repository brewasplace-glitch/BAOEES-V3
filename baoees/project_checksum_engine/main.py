import hashlib
import json
from datetime import datetime
from pathlib import Path


class ProjectChecksumEngine:

    def __init__(self):
        self.checksum_result = {}

    def create_file_manifest(
        self,
        project_result=None,
        storage_result=None,
        audit_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        audit_result = audit_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        runtime_logs_dir = Path(
            folder_structure.get(
                "runtime_logs",
                project_output_dir / "08_runtime_logs"
            )
        )

        runtime_logs_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        manifest_file = runtime_logs_dir / f"{project_id}_file_manifest.json"

        file_records = self.scan_project_files(
            project_output_dir=project_output_dir
        )

        manifest_data = {
            "engine": "ProjectChecksumEngine",
            "version": "1.0",
            "status": "PROJECT_FILE_MANIFEST_OPGESLAGEN",
            "calculation_level": "SHA256 file integrity manifest",
            "project_id": project_id,
            "project_name": project_name,
            "project_output_dir": str(project_output_dir),
            "file_count": len(file_records),
            "files": file_records,
            "audit_status": audit_result.get("status", "ONBEKEND"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Dit file manifest registreert SHA256-checksums, bestandsgrootte en wijzigingsdatum "
                "van projectoutput. Hiermee kan later worden gecontroleerd of bestanden gewijzigd zijn."
            )
        }

        manifest_result = self.write_json_file(
            file_path=manifest_file,
            data=manifest_data
        )

        self.checksum_result = {
            "engine": "ProjectChecksumEngine",
            "version": "1.0",
            "status": "PROJECT_FILE_MANIFEST_OPGESLAGEN",
            "calculation_level": "file integrity / SHA256 checksum export",
            "project_id": project_id,
            "project_name": project_name,
            "project_output_dir": str(project_output_dir),
            "runtime_logs_dir": str(runtime_logs_dir),
            "manifest_file": manifest_result,
            "file_count": len(file_records),
            "total_size_bytes": self.total_size(file_records),
            "warnings": self.build_warnings(manifest_result, file_records),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Checksum / File Integrity Engine v1.0 maakt een eerste SHA256-manifest. "
                "Latere versies kunnen digitale ondertekening, Git commit hash, immutable auditlogs "
                "en vergelijking tussen runs toevoegen."
            )
        }

        return self.checksum_result

    def scan_project_files(self, project_output_dir):
        project_output_dir = Path(project_output_dir)
        file_records = []

        if not project_output_dir.exists():
            return file_records

        for file_path in sorted(project_output_dir.rglob("*")):
            if not file_path.is_file():
                continue

            if file_path.name.endswith(".tmp"):
                continue

            file_records.append(
                self.build_file_record(
                    project_output_dir=project_output_dir,
                    file_path=file_path
                )
            )

        return file_records

    def build_file_record(self, project_output_dir, file_path):
        file_path = Path(file_path)

        try:
            relative_path = file_path.relative_to(project_output_dir)
        except Exception:
            relative_path = file_path

        stat = file_path.stat()

        return {
            "relative_path": str(relative_path).replace("\\", "/"),
            "absolute_path": str(file_path),
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "sha256": self.sha256_file(file_path),
            "category": self.categorize_file(file_path)
        }

    def sha256_file(self, file_path):
        sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as file:
                for block in iter(lambda: file.read(1024 * 1024), b""):
                    sha256.update(block)

            return sha256.hexdigest()

        except Exception as error:
            return f"FOUT: {error}"

    def categorize_file(self, file_path):
        path_text = str(file_path).replace("\\", "/").lower()
        extension = file_path.suffix.lower()

        if "/01_reports/" in path_text:
            return "rapport"

        if "/02_drawings/" in path_text:
            return "pdf_tekening"

        if "/03_cad/" in path_text:
            return "cad_dxf"

        if "/04_calculations/" in path_text:
            return "berekening"

        if "/05_permits/" in path_text:
            return "vergunning"

        if "/06_sources/" in path_text:
            return "bronregistratie"

        if "/07_digital_twin/" in path_text:
            return "digital_twin"

        if "/08_runtime_logs/" in path_text:
            return "runtime_log"

        if "/09_exports/" in path_text:
            return "export"

        if "/10_zip/" in path_text:
            return "zip"

        if extension in [".pdf", ".docx", ".md", ".txt"]:
            return "document"

        if extension in [".dxf", ".dwg", ".ifc"]:
            return "cad"

        if extension in [".csv", ".xlsx"]:
            return "tabel"

        if extension in [".json"]:
            return "json"

        if extension in [".html"]:
            return "dashboard"

        return "overig"

    def write_json_file(self, file_path, data):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def total_size(self, file_records):
        total = 0

        for record in file_records:
            total += record.get("size_bytes", 0)

        return total

    def build_warnings(self, manifest_result, file_records):
        warnings = []

        if manifest_result.get("status") != "OPGESLAGEN":
            warnings.append("File manifest is niet opgeslagen.")

        if not file_records:
            warnings.append("Geen projectbestanden gevonden voor checksum-manifest.")

        failed_hashes = [
            record for record in file_records
            if str(record.get("sha256", "")).startswith("FOUT:")
        ]

        if failed_hashes:
            warnings.append(f"{len(failed_hashes)} bestanden konden niet worden gehasht.")

        if not warnings:
            warnings.append("Geen kritieke checksum/file-integrity-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_CHECKSUM_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste integriteitslaag voor projectoutput. "
                "De volgende stap is het manifest koppelen aan de audit trail, dashboard en finale ZIP."
            ),
            "next_steps": [
                "ProjectChecksumEngine koppelen aan BAOEES Core",
                "file manifest opnemen in ZIP-export",
                "checksumresultaat opnemen in audit trail",
                "hashcontrolefunctie toevoegen",
                "verschillen tussen runs tonen",
                "Git commit hash toevoegen",
                "digitale ondertekening toevoegen"
            ]
        }

    def get_checksum_result(self):
        return self.checksum_result

    def run(self):
        print("Project Checksum / File Integrity Engine actief")