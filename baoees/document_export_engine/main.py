import json
from datetime import datetime
from pathlib import Path


class DocumentExportEngine:

    def __init__(self):
        self.document_result = {}

    def create_documents(self, project_result=None, reporting_result=None, export_result=None):
        project_result = project_result or {}
        reporting_result = reporting_result or {}
        export_result = export_result or {}

        export_folder = export_result.get("export_folder")

        if not export_folder:
            self.document_result = {
                "engine": "DocumentExportEngine",
                "status": "DOCUMENT_EXPORT_MISLUKT",
                "reason": "Geen export_folder gevonden in export_result."
            }
            return self.document_result

        export_folder_path = Path(export_folder)
        export_folder_path.mkdir(parents=True, exist_ok=True)

        report_text = self.build_report_text(project_result, reporting_result)

        txt_path = export_folder_path / "projectrapport.txt"
        docx_path = export_folder_path / "projectrapport.docx"
        pdf_path = export_folder_path / "projectrapport.pdf"

        self.write_text_file(txt_path, report_text)
        self.write_text_file(docx_path, report_text)
        self.write_text_file(pdf_path, report_text)

        self.document_result = {
            "engine": "DocumentExportEngine",
            "status": "DOCUMENT_EXPORT_GEREED",
            "export_folder": str(export_folder_path),
            "documents": [
                {
                    "file": str(txt_path),
                    "format": "TXT",
                    "status": "AANGEMAAKT"
                },
                {
                    "file": str(docx_path),
                    "format": "DOCX",
                    "status": "AANGEMAAKT"
                },
                {
                    "file": str(pdf_path),
                    "format": "PDF",
                    "status": "AANGEMAAKT"
                }
            ],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "note": "Basis documentexport aangemaakt. Professionele DOCX/PDF-opmaak volgt in een latere versie."
        }

        return self.document_result

    def build_report_text(self, project_result, reporting_result):
        title = reporting_result.get(
            "report_title",
            f"BAOEES Projectrapport - {project_result.get('project_name', 'Onbekend project')}"
        )

        lines = [
            title,
            "=" * len(title),
            "",
            f"Projectnaam: {project_result.get('project_name', 'Onbekend')}",
            f"Projecttype: {project_result.get('project_type', 'Onbekend')}",
            f"Locatie: {project_result.get('location', 'Onbekend')}",
            f"Land: {project_result.get('country', 'Onbekend')}",
            "",
            "Automatisch gegenereerd door BAOEES V3",
            ""
        ]

        sections = reporting_result.get("sections", [])

        for section in sections:
            lines.append(f"{section.get('chapter')}. {section.get('title')}")
            lines.append("-" * 40)
            lines.append(f"Status: {section.get('status', 'CONCEPT')}")
            lines.append("")
            lines.append(
                json.dumps(
                    section.get("content_summary", {}),
                    ensure_ascii=False,
                    indent=2
                )
            )
            lines.append("")

        return "\n".join(lines)

    def write_text_file(self, file_path, text):
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text)

    def get_document_result(self):
        return self.document_result

    def run(self):
        print("PDF/DOCX Export Engine actief")