from __future__ import annotations

import html
import json
import re
import sys
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.project_analyzer.project_report_bib_engine import ProjectReportBibEngine


class ProjectReportExportEngine:
    """
    PROJECT PHOENIX / BAOEES
    Project Report Export Engine v4.2

    Doel:
    - Leest project_report_bib_package.json.
    - Exporteert het projectrapport naar DOCX.
    - Exporteert het projectrapport naar PDF.
    - Maakt exportlog en HTML-dashboard.
    """

    ENGINE_NAME = "Project Phoenix Project Report Export Engine"
    ENGINE_VERSION = "v4.2"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        report_package_path: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.report_package_path = (
            Path(report_package_path)
            if report_package_path
            else self.project_output_root / "project_report_bib_package.json"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh_report: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or self.default_project_context()

        report_status = self.ensure_report_package(
            project_context=project_context,
            force_refresh_report=force_refresh_report,
        )

        package = self.read_json(self.report_package_path)
        sections = package.get("report_sections", [])

        title = "PROJECT PHOENIX / BAOEES PROJECTRAPPORT"
        subtitle = "Automatisch rapport vanuit BIB, AAIE en Geo/Foundation"

        docx_path = self.project_output_root / "project_report_bib_report.docx"
        pdf_path = self.project_output_root / "project_report_bib_report.pdf"
        log_path = self.project_output_root / "project_report_export_log.json"
        dashboard_path = self.project_output_root / "project_report_export_dashboard.html"

        self.write_docx_report(
            path=docx_path,
            title=title,
            subtitle=subtitle,
            sections=sections,
            package=package,
        )

        self.write_pdf_report(
            path=pdf_path,
            title=title,
            subtitle=subtitle,
            sections=sections,
            package=package,
        )

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Projectrapport exporteren naar DOCX en PDF.",
            "project_context": project_context,
            "report_status": report_status,
            "report_package_path": str(self.report_package_path),
            "section_count": len(sections),
            "outputs": {
                "docx_path": str(docx_path),
                "pdf_path": str(pdf_path),
                "log_path": str(log_path),
                "dashboard_path": str(dashboard_path),
            },
            "warnings": self.build_warnings(
                package=package,
                sections=sections,
                docx_path=docx_path,
                pdf_path=pdf_path,
            ),
            "file_checks": [],
            "next_steps": [
                "Koppel deze export-engine in v4.3 aan de Project Analyzer hoofdworkflow.",
                "Laat ieder projectrapport standaard DOCX en PDF genereren.",
                "Voeg later professionele opmaak, inhoudsopgave, paginanummers en bijlagen toe.",
                "Laat STEE-bronnenregister en AAIE-aannameslog als vaste bijlagen opnemen.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(log_path, result)

        result["file_checks"] = self.build_file_checks(
            [
                docx_path,
                pdf_path,
                log_path,
                dashboard_path,
            ]
        )

        dashboard_path.write_text(
            self.build_html_dashboard(result),
            encoding="utf-8",
        )

        result["file_checks"] = self.build_file_checks(
            [
                docx_path,
                pdf_path,
                log_path,
                dashboard_path,
            ]
        )

        self.write_json(log_path, result)

        return result

    def ensure_report_package(
        self,
        project_context: Dict[str, Any],
        force_refresh_report: bool,
    ) -> Dict[str, Any]:
        if self.report_package_path.exists() and not force_refresh_report:
            return {
                "status": "AANWEZIG",
                "message": "Project Report BIB package bestond al.",
                "path": str(self.report_package_path),
            }

        engine = ProjectReportBibEngine(project_output_root=self.project_output_root)
        result = engine.run(
            project_context=project_context,
            force_refresh_geo=force_refresh_report,
        )

        return {
            "status": "GEGENEREERD",
            "message": "Project Report BIB package is gegenereerd of vernieuwd.",
            "path": str(self.report_package_path),
            "engine_result_status": result.get("status"),
        }

    def write_docx_report(
        self,
        path: Path,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]],
        package: Dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        document_xml = self.build_docx_document_xml(
            title=title,
            subtitle=subtitle,
            sections=sections,
            package=package,
        )

        content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

        rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr>
      <w:sz w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="36"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading 1"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="30"/>
    </w:rPr>
  </w:style>
</w:styles>
"""

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as docx:
            docx.writestr("[Content_Types].xml", content_types_xml)
            docx.writestr("_rels/.rels", rels_xml)
            docx.writestr("word/document.xml", document_xml)
            docx.writestr("word/styles.xml", styles_xml)

    def build_docx_document_xml(
        self,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]],
        package: Dict[str, Any],
    ) -> str:
        paragraphs = [
            self.docx_paragraph(title, style="Title"),
            self.docx_paragraph(subtitle),
            self.docx_paragraph(
                f"Automatisch gegenereerd: {datetime.now().isoformat(timespec='seconds')}"
            ),
            self.docx_paragraph(
                "Concept startpakket. Definitieve engineering vereist projectdata, controle en goedkeuring."
            ),
            self.docx_paragraph(""),
        ]

        for section in sections:
            heading = f"{section.get('order', '')}. {section.get('title', '')}"
            paragraphs.append(self.docx_paragraph(heading, style="Heading1"))

            for item in section.get("content", []):
                paragraphs.append(self.docx_paragraph(f"• {self.clean_text(str(item))}"))

            paragraphs.append(self.docx_paragraph(""))

        warnings = package.get("warnings", [])

        if warnings:
            paragraphs.append(self.docx_paragraph("Waarschuwingen", style="Heading1"))

            for warning in warnings:
                paragraphs.append(self.docx_paragraph(f"• {self.clean_text(str(warning))}"))

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

    def docx_paragraph(self, text: str, style: Optional[str] = None) -> str:
        cleaned = self.clean_text(text)
        escaped_text = xml_escape(cleaned)

        style_xml = ""

        if style:
            style_xml = f'<w:pPr><w:pStyle w:val="{xml_escape(style)}"/></w:pPr>'

        return f"""
<w:p>
  {style_xml}
  <w:r>
    <w:t xml:space="preserve">{escaped_text}</w:t>
  </w:r>
</w:p>
"""

    def write_pdf_report(
        self,
        path: Path,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]],
        package: Dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = self.build_pdf_lines(
            title=title,
            subtitle=subtitle,
            sections=sections,
            package=package,
        )

        pages = self.paginate_lines(lines, max_lines_per_page=48)
        pdf_bytes = self.build_simple_pdf(pages)
        path.write_bytes(pdf_bytes)

    def build_pdf_lines(
        self,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]],
        package: Dict[str, Any],
    ) -> List[str]:
        lines = [
            title,
            subtitle,
            f"Automatisch gegenereerd: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "Concept startpakket. Definitieve engineering vereist projectdata, controle en goedkeuring.",
            "",
        ]

        for section in sections:
            lines.append(f"{section.get('order', '')}. {section.get('title', '')}")
            lines.append("")

            for item in section.get("content", []):
                wrapped = textwrap.wrap(self.clean_text(str(item)), width=95)

                if wrapped:
                    lines.append(f"- {wrapped[0]}")

                    for continuation in wrapped[1:]:
                        lines.append(f"  {continuation}")
                else:
                    lines.append("-")

            lines.append("")

        warnings = package.get("warnings", [])

        if warnings:
            lines.append("WAARSCHUWINGEN")
            lines.append("")

            for warning in warnings:
                lines.append(f"- {self.clean_text(str(warning))}")

        return lines

    def paginate_lines(
        self,
        lines: List[str],
        max_lines_per_page: int,
    ) -> List[List[str]]:
        pages: List[List[str]] = []
        current_page: List[str] = []

        for line in lines:
            current_page.append(line)

            if len(current_page) >= max_lines_per_page:
                pages.append(current_page)
                current_page = []

        if current_page:
            pages.append(current_page)

        return pages or [["Leeg rapport."]]

    def build_simple_pdf(self, pages: List[List[str]]) -> bytes:
        objects: List[bytes] = []

        def safe_pdf_text(value: str) -> str:
            value = self.clean_text(value)
            value = value.encode("latin-1", errors="replace").decode("latin-1")
            value = value.replace("\\", "\\\\")
            value = value.replace("(", "\\(")
            value = value.replace(")", "\\)")
            return value

        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

        page_ids = []
        content_ids = []

        for index in range(len(pages)):
            page_ids.append(4 + index * 2)
            content_ids.append(5 + index * 2)

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)

        objects.append(
            f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("latin-1")
        )

        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        for page_index, page_lines in enumerate(pages):
            content_id = content_ids[page_index]

            page_object = (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )

            objects.append(page_object.encode("latin-1"))

            stream_parts = [
                "BT",
                "/F1 10 Tf",
                "50 800 Td",
            ]

            for line_index, line in enumerate(page_lines):
                safe_line = safe_pdf_text(line)

                if line_index == 0:
                    stream_parts.append(f"({safe_line}) Tj")
                else:
                    stream_parts.append(f"0 -14 Td ({safe_line}) Tj")

            stream_parts.append("ET")

            stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

            content_object = (
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream"
            )

            objects.append(content_object)

        pdf = bytearray()
        pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = [0]

        for object_id, object_bytes in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
            pdf.extend(object_bytes)
            pdf.extend(b"\nendobj\n")

        xref_position = len(pdf)

        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")

        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

        pdf.extend(
            (
                f"trailer\n"
                f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_position}\n"
                f"%%EOF\n"
            ).encode("ascii")
        )

        return bytes(pdf)

    def build_html_dashboard(self, result: Dict[str, Any]) -> str:
        outputs = result.get("outputs", {})
        checks = result.get("file_checks", [])
        warnings = result.get("warnings", [])

        check_rows = ""

        for check in checks:
            check_rows += (
                "<tr>"
                f"<td>{self.esc(check.get('path', ''))}</td>"
                f"<td>{self.esc(check.get('exists', ''))}</td>"
                f"<td>{self.esc(check.get('size_bytes', ''))}</td>"
                "</tr>"
            )

        warning_items = ""

        for warning in warnings:
            warning_items += f"<li>{self.esc(warning)}</li>"

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Report Export Dashboard</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #050816;
      color: #f8fafc;
      line-height: 1.5;
    }}
    header {{
      padding: 34px 42px;
      background: #0f172a;
      border-bottom: 1px solid #334155;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      margin-top: 18px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0f172a;
      color: #bfdbfe;
    }}
    a {{
      color: #93c5fd;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT REPORT EXPORT DASHBOARD</h1>
    <p>DOCX- en PDF-export van het Project Phoenix / BAOEES projectrapport.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>DOCX</h3>
        <p><a href="project_report_bib_report.docx">Open DOCX</a></p>
        <p class="muted">{self.esc(outputs.get("docx_path", ""))}</p>
      </div>
      <div class="card">
        <h3>PDF</h3>
        <p><a href="project_report_bib_report.pdf">Open PDF</a></p>
        <p class="muted">{self.esc(outputs.get("pdf_path", ""))}</p>
      </div>
      <div class="card">
        <h3>Bronpakket</h3>
        <p class="muted">{self.esc(result.get("report_package_path", ""))}</p>
      </div>
    </section>

    <h2>Bestandscontrole</h2>
    <table>
      <thead>
        <tr>
          <th>Pad</th>
          <th>Bestaat</th>
          <th>Grootte bytes</th>
        </tr>
      </thead>
      <tbody>
        {check_rows}
      </tbody>
    </table>

    <h2>Waarschuwingen</h2>
    <ul>
      {warning_items}
    </ul>
  </main>
</body>
</html>
"""

    def build_file_checks(self, paths: List[Path]) -> List[Dict[str, Any]]:
        return [
            {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
            for path in paths
        ]

    def build_warnings(
        self,
        package: Dict[str, Any],
        sections: List[Dict[str, Any]],
        docx_path: Path,
        pdf_path: Path,
    ) -> List[str]:
        warnings: List[str] = []

        if not package:
            warnings.append("Rapportpakket ontbreekt of kon niet worden gelezen.")

        if not sections:
            warnings.append("Geen rapportsecties gevonden.")

        if not docx_path.exists():
            warnings.append("DOCX-export is niet aangemaakt.")

        if not pdf_path.exists():
            warnings.append("PDF-export is niet aangemaakt.")

        if docx_path.exists() and docx_path.stat().st_size < 1000:
            warnings.append("DOCX-export lijkt te klein.")

        if pdf_path.exists() and pdf_path.stat().st_size < 1000:
            warnings.append("PDF-export lijkt te klein.")

        if not warnings:
            warnings.append("Geen kritieke Project Report Export-waarschuwingen.")

        return warnings

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default Project Phoenix Report Export",
            "project_type": "bouw",
            "purpose": "Automatische DOCX/PDF-export vanuit Project Report BIB Engine.",
            "phase": "concept",
        }

    def clean_text(self, value: str) -> str:
        value = value.replace("\r", " ")
        value = value.replace("\n", " ")
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def read_json(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = ProjectReportExportEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()