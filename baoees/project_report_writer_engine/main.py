from datetime import datetime
from pathlib import Path


class ProjectReportWriterEngine:

    def __init__(self):
        self.report_writer_result = {}

    def write_project_report(
        self,
        project_result=None,
        storage_result=None,
        config_result=None,
        selector_result=None,
        reporting_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        cost_result=None,
        planning_result=None,
        validation_result=None,
        runtime_result=None,
        zip_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        config_result = config_result or {}
        selector_result = selector_result or {}
        reporting_result = reporting_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        validation_result = validation_result or {}
        runtime_result = runtime_result or {}
        zip_result = zip_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        reports_dir = Path(
            folder_structure.get(
                "reports",
                project_output_dir / "01_reports"
            )
        )

        reports_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")

        markdown_file = reports_dir / f"{project_id}_project_report.md"
        text_file = reports_dir / f"{project_id}_project_report.txt"

        report_content = self.build_report_content(
            project_result=project_result,
            storage_result=storage_result,
            config_result=config_result,
            selector_result=selector_result,
            reporting_result=reporting_result,
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            cost_result=cost_result,
            planning_result=planning_result,
            validation_result=validation_result,
            runtime_result=runtime_result,
            zip_result=zip_result
        )

        written_files = [
            self.write_text_file(markdown_file, report_content),
            self.write_text_file(text_file, report_content)
        ]

        self.report_writer_result = {
            "engine": "ProjectReportWriterEngine",
            "version": "1.0",
            "status": "PROJECT_REPORT_FILES_OPGESLAGEN",
            "calculation_level": "Markdown/TXT rapportexport",
            "project_id": project_id,
            "project_name": project_result.get("project_name", "Onbekend project"),
            "reports_dir": str(reports_dir),
            "written_files": written_files,
            "written_file_count": len(written_files),
            "warnings": self.build_warnings(written_files),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Report Writer Engine v1.0 schrijft eerst Markdown- en TXT-rapporten. "
                "In de volgende versie kan dit worden uitgebreid naar echte PDF- en DOCX-generatie."
            )
        }

        return self.report_writer_result

    def build_report_content(
        self,
        project_result,
        storage_result,
        config_result,
        selector_result,
        reporting_result,
        geo_result,
        structural_result,
        permit_result,
        cost_result,
        planning_result,
        validation_result,
        runtime_result,
        zip_result
    ):
        project_name = project_result.get("project_name", "Onbekend project")
        project_type = project_result.get("project_type", "Onbekend")
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")
        project_id = storage_result.get("project_id", "unknown_project")

        lines = []

        lines.append(f"# BAOEES Projectrapport")
        lines.append("")
        lines.append(f"## 1. Projectgegevens")
        lines.append("")
        lines.append(f"- Project-ID: {project_id}")
        lines.append(f"- Projectnaam: {project_name}")
        lines.append(f"- Projecttype: {project_type}")
        lines.append(f"- Locatie: {location}")
        lines.append(f"- Land: {country}")
        lines.append(f"- Runtime mode: {project_result.get('runtime_mode', 'onbekend')}")
        lines.append(f"- Rapportdatum: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")

        lines.append("## 2. Projectselectie en invoer")
        lines.append("")
        lines.append(f"- Project Selector status: {selector_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Project Config status: {config_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Config-pad: {config_result.get('config_path', 'ONBEKEND')}")
        lines.append("")

        lines.append("## 3. Rapportagestructuur")
        lines.append("")
        lines.append(f"- Reporting Engine status: {reporting_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Rapportage niveau: {reporting_result.get('calculation_level', 'ONBEKEND')}")
        lines.append("")

        lines.append("## 4. Geotechniek")
        lines.append("")
        lines.append(f"- Geo Engine status: {geo_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Geo advies: {geo_result.get('recommendation', 'Niet beschikbaar')}")
        lines.append("")

        lines.append("## 5. Constructie")
        lines.append("")
        lines.append(f"- Structural Engine status: {structural_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Constructief advies: {structural_result.get('recommendation', 'Niet beschikbaar')}")
        lines.append("")

        lines.append("## 6. Vergunningen")
        lines.append("")
        lines.append(f"- Permit Engine status: {permit_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Vergunningadvies: {permit_result.get('recommendation', 'Niet beschikbaar')}")
        lines.append("")

        lines.append("## 7. Kosten en planning")
        lines.append("")
        lines.append(f"- Cost Engine status: {cost_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Planning Engine status: {planning_result.get('status', 'ONBEKEND')}")
        lines.append("")

        lines.append("## 8. QA/QC en validatie")
        lines.append("")
        lines.append(f"- Validation Engine status: {validation_result.get('status', 'ONBEKEND')}")
        lines.append(f"- Go/No-Go advies: {validation_result.get('go_no_go_advice', 'Niet beschikbaar')}")
        lines.append("")

        lines.append("## 9. Runtime en export")
        lines.append("")
        lines.append(f"- Runtime Engine status: {runtime_result.get('status', 'ONBEKEND')}")
        lines.append(f"- ZIP Engine status: {zip_result.get('status', 'ONBEKEND')}")
        lines.append(f"- ZIP-bestand: {zip_result.get('zip_file_path', 'Nog niet beschikbaar')}")
        lines.append("")

        lines.append("## 10. Projectmap")
        lines.append("")
        lines.append(f"- Project outputmap: {storage_result.get('project_output_dir', 'ONBEKEND')}")
        lines.append("")

        lines.append("## 11. Opmerking")
        lines.append("")
        lines.append(
            "Dit is een automatisch gegenereerd BAOEES-conceptrapport. "
            "De inhoud moet per project nog technisch, juridisch en inhoudelijk worden gecontroleerd."
        )
        lines.append("")

        return "\n".join(lines)

    def write_text_file(self, file_path, content):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)

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

    def build_warnings(self, written_files):
        warnings = []

        for file_info in written_files:
            if file_info.get("status") != "OPGESLAGEN":
                warnings.append(
                    f"Rapportbestand niet opgeslagen: {file_info.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke rapportage-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_REPORT_WRITER_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste fysieke rapportgenerator. "
                "De volgende stap is uitbreiding naar echte PDF- en DOCX-bestanden."
            ),
            "next_steps": [
                "ProjectReportWriterEngine koppelen aan BAOEES Core",
                "rapport opnemen in ZIP-export",
                "PDF-generatie toevoegen",
                "DOCX-generatie toevoegen",
                "rapportopmaak professionaliseren",
                "inhoud uitbreiden per discipline"
            ]
        }

    def get_report_writer_result(self):
        return self.report_writer_result

    def run(self):
        print("Project Report Writer Engine actief")