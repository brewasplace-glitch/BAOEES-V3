import json
from datetime import datetime
from pathlib import Path


class ProjectAuditTrailEngine:

    def __init__(self):
        self.audit_result = {}

    def register_project_run(
        self,
        project_result=None,
        storage_result=None,
        selector_result=None,
        config_result=None,
        runtime_result=None,
        validation_result=None,
        file_writer_result=None,
        report_writer_result=None,
        pdf_docx_result=None,
        dxf_writer_result=None,
        drawing_pdf_result=None,
        csv_excel_result=None,
        xlsx_result=None,
        html_dashboard_result=None,
        zip_result=None,
        index_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        selector_result = selector_result or {}
        config_result = config_result or {}
        runtime_result = runtime_result or {}
        validation_result = validation_result or {}
        file_writer_result = file_writer_result or {}
        report_writer_result = report_writer_result or {}
        pdf_docx_result = pdf_docx_result or {}
        dxf_writer_result = dxf_writer_result or {}
        drawing_pdf_result = drawing_pdf_result or {}
        csv_excel_result = csv_excel_result or {}
        xlsx_result = xlsx_result or {}
        html_dashboard_result = html_dashboard_result or {}
        zip_result = zip_result or {}
        index_result = index_result or {}

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

        projects_root = project_output_dir.parent
        projects_root.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        audit_file = runtime_logs_dir / f"{project_id}_audit_trail.json"
        central_history_file = projects_root / "project_run_history.json"

        run_record = self.build_run_record(
            project_id=project_id,
            project_name=project_name,
            project_result=project_result,
            storage_result=storage_result,
            selector_result=selector_result,
            config_result=config_result,
            runtime_result=runtime_result,
            validation_result=validation_result,
            file_writer_result=file_writer_result,
            report_writer_result=report_writer_result,
            pdf_docx_result=pdf_docx_result,
            dxf_writer_result=dxf_writer_result,
            drawing_pdf_result=drawing_pdf_result,
            csv_excel_result=csv_excel_result,
            xlsx_result=xlsx_result,
            html_dashboard_result=html_dashboard_result,
            zip_result=zip_result,
            index_result=index_result
        )

        project_audit_result = self.append_record_to_json_log(
            file_path=audit_file,
            root_key="audit_trail",
            record=run_record
        )

        central_history_result = self.append_record_to_json_log(
            file_path=central_history_file,
            root_key="project_run_history",
            record=run_record
        )

        self.audit_result = {
            "engine": "ProjectAuditTrailEngine",
            "version": "1.0",
            "status": "PROJECT_AUDIT_TRAIL_OPGESLAGEN",
            "calculation_level": "project run audit trail en centrale run history",
            "project_id": project_id,
            "project_name": project_name,
            "audit_file": project_audit_result,
            "central_history_file": central_history_result,
            "run_record": run_record,
            "warnings": self.build_warnings(project_audit_result, central_history_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Run Log / Audit Trail Engine v1.0 registreert projectruns lokaal "
                "in JSON-bestanden. Latere versies kunnen immutable logs, checksums, gebruikers-ID, "
                "Git commit hash, versiebeheer en digitale ondertekening toevoegen."
            )
        }

        return self.audit_result

    def build_run_record(
        self,
        project_id,
        project_name,
        project_result,
        storage_result,
        selector_result,
        config_result,
        runtime_result,
        validation_result,
        file_writer_result,
        report_writer_result,
        pdf_docx_result,
        dxf_writer_result,
        drawing_pdf_result,
        csv_excel_result,
        xlsx_result,
        html_dashboard_result,
        zip_result,
        index_result
    ):
        return {
            "run_id": self.create_run_id(project_id),
            "run_timestamp": datetime.now().isoformat(timespec="seconds"),
            "project_id": project_id,
            "project_name": project_name,
            "project_type": project_result.get("project_type", "Onbekend"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "runtime_mode": project_result.get("runtime_mode", "onbekend"),
            "selected_project_id": project_result.get("selected_project_id", "ONBEKEND"),
            "project_output_dir": storage_result.get("project_output_dir", "ONBEKEND"),
            "config_path": config_result.get("config_path", "ONBEKEND"),
            "selector_status": selector_result.get("status", "ONBEKEND"),
            "runtime_status": runtime_result.get("status", "ONBEKEND"),
            "validation_status": validation_result.get("status", "ONBEKEND"),
            "go_no_go_advice": validation_result.get("go_no_go_advice", "Niet beschikbaar"),
            "exports": {
                "json_files": self.status_block(file_writer_result),
                "markdown_txt_report": self.status_block(report_writer_result),
                "pdf_docx_report": self.status_block(pdf_docx_result),
                "dxf_drawings": self.status_block(dxf_writer_result),
                "drawing_pdfs": self.status_block(drawing_pdf_result),
                "csv_excel": self.status_block(csv_excel_result),
                "xlsx": self.status_block(xlsx_result),
                "html_dashboard": self.status_block(html_dashboard_result),
                "zip_export": self.status_block(zip_result),
                "index_startpage": self.status_block(index_result)
            },
            "important_paths": {
                "project_report_pdf": self.project_file_path(storage_result, "01_reports", f"{project_id}_project_report.pdf"),
                "project_report_docx": self.project_file_path(storage_result, "01_reports", f"{project_id}_project_report.docx"),
                "project_dashboard_html": self.project_file_path(storage_result, "09_exports", f"{project_id}_dashboard.html"),
                "project_tables_xlsx": self.project_file_path(storage_result, "09_exports", f"{project_id}_project_tables.xlsx"),
                "project_zip": self.project_file_path(storage_result, "10_zip", f"{project_id}_project_export.zip"),
                "digital_twin_json": self.project_file_path(storage_result, "07_digital_twin", "digital_twin.json"),
                "source_register_json": self.project_file_path(storage_result, "06_sources", "source_register.json"),
                "runtime_log_json": self.project_file_path(storage_result, "08_runtime_logs", "runtime_log.json")
            }
        }

    def create_run_id(self, project_id):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{project_id}_{stamp}"

    def status_block(self, result):
        result = result or {}

        block = {
            "engine": result.get("engine", "ONBEKEND"),
            "status": result.get("status", "ONBEKEND"),
            "created_at": result.get("created_at", ""),
            "warning_count": len(result.get("warnings", [])) if isinstance(result.get("warnings", []), list) else 0
        }

        if "written_file_count" in result:
            block["written_file_count"] = result.get("written_file_count")

        if "worksheet_count" in result:
            block["worksheet_count"] = result.get("worksheet_count")

        if "dashboard_file" in result:
            block["dashboard_file"] = result.get("dashboard_file")

        if "xlsx_file" in result:
            block["xlsx_file"] = result.get("xlsx_file")

        if "zip_file_path" in result:
            block["zip_file_path"] = result.get("zip_file_path")

        if "index_file" in result:
            block["index_file"] = result.get("index_file")

        return block

    def project_file_path(self, storage_result, folder_key, filename):
        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        folder_path = Path(
            folder_structure.get(
                folder_key,
                project_output_dir / folder_key
            )
        )

        return str(folder_path / filename)

    def append_record_to_json_log(self, file_path, root_key, record):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            existing_data = self.read_json_file(file_path=file_path)

            if not isinstance(existing_data, dict):
                existing_data = {}

            records = existing_data.get(root_key, [])

            if not isinstance(records, list):
                records = []

            records.append(record)

            output_data = {
                root_key: records,
                "record_count": len(records),
                "last_updated": datetime.now().isoformat(timespec="seconds")
            }

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(output_data, file, indent=2, ensure_ascii=False)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                "record_count": len(records)
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "record_count": 0,
                "error": str(error)
            }

    def read_json_file(self, file_path):
        file_path = Path(file_path)

        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

        except Exception:
            return {}

    def build_warnings(self, project_audit_result, central_history_result):
        warnings = []

        if project_audit_result.get("status") != "OPGESLAGEN":
            warnings.append("Project audit trail is niet opgeslagen.")

        if central_history_result.get("status") != "OPGESLAGEN":
            warnings.append("Centrale project run history is niet opgeslagen.")

        if not warnings:
            warnings.append("Geen kritieke audit trail-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_AUDIT_TRAIL_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste auditlaag voor herleidbaarheid van projectruns. "
                "De volgende stap is vastleggen van Git commit hash, checksums per outputbestand, "
                "gebruikersnaam, machine-ID en softwareversie."
            ),
            "next_steps": [
                "ProjectAuditTrailEngine koppelen aan BAOEES Core",
                "audit trail opnemen in ZIP-export",
                "Git commit hash toevoegen",
                "checksums per bestand toevoegen",
                "engineversies automatisch uitlezen",
                "centrale project_run_history uitbreiden",
                "auditlog tonen in HTML-dashboard",
                "immutable auditlog toevoegen"
            ]
        }

    def get_audit_result(self):
        return self.audit_result

    def run(self):
        print("Project Run Log / Audit Trail Engine actief")