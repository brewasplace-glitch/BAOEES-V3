from __future__ import annotations

import html
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectReportExportEngine:
    ENGINE_NAME = "Project Phoenix Project Report Export Engine"
    ENGINE_VERSION = "v6.1"

    def __init__(self, project_output_root: Optional[str | Path] = None) -> None:
        if project_output_root:
            self.project_output_root = Path(project_output_root)
        else:
            self.project_output_root = PROJECT_ROOT / "outputs" / "projects"

        self.report_package_path = (
            self.project_output_root
            / "project_report_bib_package.json"
        )

        self.docx_path = (
            self.project_output_root
            / "project_report_bib_report.docx"
        )

        self.pdf_path = (
            self.project_output_root
            / "project_report_bib_report.pdf"
        )

        self.export_log_path = (
            self.project_output_root
            / "project_report_export_log.json"
        )

        self.export_dashboard_path = (
            self.project_output_root
            / "project_report_export_dashboard.html"
        )

    def run(self, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        report_package = self.read_json(self.report_package_path)
        report_lines = self.build_report_lines(report_package)

        docx_status = self.write_docx(self.docx_path, report_lines)
        pdf_status = self.write_pdf(self.pdf_path, report_lines)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "report_package_path": str(self.report_package_path),
            "docx_path": str(self.docx_path),
            "pdf_path": str(self.pdf_path),
            "export_log_path": str(self.export_log_path),
            "export_dashboard_path": str(self.export_dashboard_path),
            "report_package_status": "GELEZEN" if report_package else "ONTBREEKT",
            "docx_status": docx_status,
            "pdf_status": pdf_status,
            "line_count": len(report_lines),
            "export_formats": [
                "DOCX",
                "PDF",
            ],
            "next_steps": [
                "Controleer het gegenereerde DOCX-bestand.",
                "Controleer het gegenereerde PDF-bestand.",
                "Koppel daarna bronvermelding en bijlagenpakket aan de export.",
            ],
        }

        self.write_json(self.export_log_path, result)
        self.write_text(self.export_dashboard_path, self.build_dashboard(result))

        return result

    def build_report_lines(self, report_package: Dict[str, Any]) -> List[str]:
        lines: List[str] = []

        lines.append("PROJECT PHOENIX PROJECTRAPPORTAGE")
        lines.append("Versie: v6.1")
        lines.append("")

        if not report_package:
            lines.append("Status: rapportagepackage ontbreekt.")
            lines.append("")
            lines.append("Voer eerst deze engine uit:")
            lines.append("baoees/project_analyzer/project_report_bib_engine.py")
            return lines

        lines.append(f"Bron engine: {report_package.get('engine', '')}")
        lines.append(f"Bron versie: {report_package.get('engine_version', '')}")
        lines.append(f"Status: {report_package.get('status', '')}")
        lines.append("")

        workflow_summary = report_package.get("workflow_summary", {})
        bib_summary = report_package.get("bib_summary", {})
        aaie_summary = report_package.get("aaie_summary", {})

        lines.append("SAMENVATTING WORKFLOW")
        lines.append(f"Workflow status: {workflow_summary.get('status', '')}")
        lines.append(f"Workflow versie: {workflow_summary.get('engine_version', '')}")
        lines.append(
            f"Aantal workflowstappen: {workflow_summary.get('workflow_steps_count', 0)}"
        )
        lines.append("")

        lines.append("SAMENVATTING BIB")
        lines.append(f"BIB status: {bib_summary.get('status', '')}")
        lines.append(f"BIB versie: {bib_summary.get('engine_version', '')}")
        lines.append(
            f"Inhoudelijk herkend: {bib_summary.get('recognized_text_items_count', 0)}"
        )
        lines.append(f"Besluiten: {bib_summary.get('decisions_count', 0)}")
        lines.append(f"Kennisitems: {bib_summary.get('knowledge_items_count', 0)}")
        lines.append(f"Acties: {bib_summary.get('actions_count', 0)}")
        lines.append("")

        lines.append("SAMENVATTING AAIE")
        lines.append(f"AAIE status: {aaie_summary.get('status', '')}")
        lines.append(f"AAIE versie: {aaie_summary.get('engine_version', '')}")
        lines.append(f"Aantal aannames: {aaie_summary.get('assumption_count', 0)}")
        lines.append("")

        report_sections = report_package.get("report_sections", [])

        if report_sections:
            lines.append("RAPPORTAGEHOOFDSTUKKEN")
            lines.append("")

            for section in report_sections:
                if not isinstance(section, dict):
                    continue

                number = section.get("number", "")
                title = section.get("title", "")
                status = section.get("status", "")
                content = section.get("content", [])

                lines.append(f"{number}. {title}")
                lines.append(f"Status: {status}")

                if isinstance(content, list):
                    for item in content:
                        lines.append(str(item))
                else:
                    lines.append(str(content))

                lines.append("")

        next_steps = report_package.get("next_steps", [])

        if next_steps:
            lines.append("VOLGENDE STAPPEN")

            for step in next_steps:
                lines.append(f"- {step}")

        return lines

    def write_docx(self, path: Path, lines: List[str]) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)

        document_xml = self.build_docx_document_xml(lines)

        content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

        rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

        document_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as docx:
            docx.writestr("[Content_Types].xml", content_types_xml)
            docx.writestr("_rels/.rels", rels_xml)
            docx.writestr("word/_rels/document.xml.rels", document_rels_xml)
            docx.writestr("word/document.xml", document_xml)

        return "OPGESLAGEN"

    def build_docx_document_xml(self, lines: List[str]) -> str:
        paragraphs: List[str] = []

        for line in lines:
            safe_line = escape(str(line))

            if safe_line.strip() == "":
                paragraphs.append("<w:p/>")
            else:
                paragraphs.append(
                    "<w:p>"
                    "<w:r>"
                    "<w:t xml:space=\"preserve\">"
                    f"{safe_line}"
                    "</w:t>"
                    "</w:r>"
                    "</w:p>"
                )

        body = "\n".join(paragraphs)

        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

    def write_pdf(self, path: Path, lines: List[str]) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)

        page_lines = self.prepare_pdf_lines(lines)
        stream = self.build_pdf_stream(page_lines)

        objects: List[str] = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]

        pdf_parts: List[bytes] = []
        pdf_parts.append(b"%PDF-1.4\n")

        offsets: List[int] = [0]

        for index, obj in enumerate(objects, start=1):
            offsets.append(sum(len(part) for part in pdf_parts))
            pdf_parts.append(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1"))

        xref_offset = sum(len(part) for part in pdf_parts)

        xref_lines = [
            "xref",
            f"0 {len(objects) + 1}",
            "0000000000 65535 f ",
        ]

        for offset in offsets[1:]:
            xref_lines.append(f"{offset:010d} 00000 n ")

        trailer = [
            "trailer",
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>",
            "startxref",
            str(xref_offset),
            "%%EOF",
        ]

        pdf_parts.append(("\n".join(xref_lines) + "\n").encode("latin-1"))
        pdf_parts.append(("\n".join(trailer) + "\n").encode("latin-1"))

        path.write_bytes(b"".join(pdf_parts))

        return "OPGESLAGEN"

    def prepare_pdf_lines(self, lines: List[str]) -> List[str]:
        prepared: List[str] = []

        for line in lines:
            clean_line = str(line).replace("\t", " ")

            if len(clean_line) > 90:
                prepared.append(clean_line[:90])
                prepared.append(clean_line[90:180])
            else:
                prepared.append(clean_line)

            if len(prepared) >= 38:
                break

        return prepared

    def build_pdf_stream(self, lines: List[str]) -> str:
        stream_lines: List[str] = []

        stream_lines.append("BT")
        stream_lines.append("/F1 10 Tf")
        stream_lines.append("50 800 Td")

        first_line = True

        for line in lines:
            safe_line = self.pdf_escape(line)

            if first_line:
                stream_lines.append(f"({safe_line}) Tj")
                first_line = False
            else:
                stream_lines.append("0 -18 Td")
                stream_lines.append(f"({safe_line}) Tj")

        stream_lines.append("ET")

        return "\n".join(stream_lines)

    def pdf_escape(self, value: Any) -> str:
        text = str(value)
        text = text.replace("\\", "\\\\")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        return text

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        html_parts = [
            "<!doctype html>",
            "<html lang=\"nl\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <title>Project Phoenix Export v6.1</title>",
            "  <style>",
            "    body { margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }",
            "    main { max-width: 1080px; margin: 0 auto; padding: 32px; }",
            "    section { background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }",
            "    h1, h2 { color: #f8fafc; }",
            "    code { color: #bfdbfe; }",
            "  </style>",
            "</head>",
            "<body>",
            "<main>",
            "  <section>",
            "    <h1>Project Phoenix Export v6.1</h1>",
            f"    <p>Status: {self.esc(result.get('status', ''))}</p>",
            "    <p>De projectrapportagepackage is gekoppeld aan DOCX/PDF-export.</p>",
            "  </section>",
            "  <section>",
            "    <h2>Exportstatus</h2>",
            f"    <p>Rapportagepackage: {self.esc(result.get('report_package_status', ''))}</p>",
            f"    <p>DOCX: {self.esc(result.get('docx_status', ''))}</p>",
            f"    <p>PDF: {self.esc(result.get('pdf_status', ''))}</p>",
            f"    <p>Aantal rapportregels: {self.esc(result.get('line_count', 0))}</p>",
            "  </section>",
            "  <section>",
            "    <h2>Bestanden</h2>",
            f"    <p><code>{self.esc(result.get('docx_path', ''))}</code></p>",
            f"    <p><code>{self.esc(result.get('pdf_path', ''))}</code></p>",
            f"    <p><code>{self.esc(result.get('export_log_path', ''))}</code></p>",
            f"    <p><code>{self.esc(result.get('export_dashboard_path', ''))}</code></p>",
            "  </section>",
            "</main>",
            "</body>",
            "</html>",
        ]

        return "\n".join(html_parts)

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


ProjectReportBibExportEngine = ProjectReportExportEngine
ProjectReportExporter = ProjectReportExportEngine


def main() -> None:
    engine = ProjectReportExportEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()