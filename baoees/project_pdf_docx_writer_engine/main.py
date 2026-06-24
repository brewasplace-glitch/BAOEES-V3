import html
import zipfile
from datetime import datetime
from pathlib import Path


class ProjectPdfDocxWriterEngine:

    def __init__(self):
        self.pdf_docx_result = {}

    def write_pdf_docx_reports(
        self,
        project_result=None,
        storage_result=None,
        report_writer_result=None,
        validation_result=None,
        runtime_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        report_writer_result = report_writer_result or {}
        validation_result = validation_result or {}
        runtime_result = runtime_result or {}

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
        project_name = project_result.get("project_name", "Onbekend project")

        report_text = self.build_report_text(
            project_result=project_result,
            storage_result=storage_result,
            validation_result=validation_result,
            runtime_result=runtime_result
        )

        pdf_path = reports_dir / f"{project_id}_project_report.pdf"
        docx_path = reports_dir / f"{project_id}_project_report.docx"

        pdf_result = self.write_basic_pdf(
            pdf_path=pdf_path,
            title=f"BAOEES Projectrapport - {project_name}",
            lines=report_text.splitlines()
        )

        docx_result = self.write_basic_docx(
            docx_path=docx_path,
            title=f"BAOEES Projectrapport - {project_name}",
            lines=report_text.splitlines()
        )

        self.pdf_docx_result = {
            "engine": "ProjectPdfDocxWriterEngine",
            "version": "1.0",
            "status": "PDF_DOCX_REPORTS_OPGESLAGEN",
            "calculation_level": "basis PDF/DOCX rapportexport",
            "project_id": project_id,
            "project_name": project_name,
            "reports_dir": str(reports_dir),
            "pdf_result": pdf_result,
            "docx_result": docx_result,
            "source_report_writer_status": report_writer_result.get("status", "ONBEKEND"),
            "runtime_status": runtime_result.get("status", "ONBEKEND"),
            "validation_status": validation_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(pdf_result, docx_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze PDF/DOCX Report Export Engine v1.0 maakt eenvoudige basisrapporten "
                "met standaard Python. Voor professionele opmaak kunnen later python-docx, "
                "ReportLab, WeasyPrint of LibreOffice-conversie worden toegevoegd."
            )
        }

        return self.pdf_docx_result

    def build_report_text(
        self,
        project_result,
        storage_result,
        validation_result,
        runtime_result
    ):
        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")
        project_type = project_result.get("project_type", "Onbekend")
        location = project_result.get("location", "Onbekend")
        country = project_result.get("country", "Onbekend")

        lines = []

        lines.append("BAOEES PROJECTRAPPORT")
        lines.append("")
        lines.append("1. PROJECTGEGEVENS")
        lines.append(f"Project-ID: {project_id}")
        lines.append(f"Projectnaam: {project_name}")
        lines.append(f"Projecttype: {project_type}")
        lines.append(f"Locatie: {location}")
        lines.append(f"Land: {country}")
        lines.append(f"Runtime mode: {project_result.get('runtime_mode', 'onbekend')}")
        lines.append(f"Rapportdatum: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")

        lines.append("2. STATUS")
        lines.append(f"Runtime status: {runtime_result.get('status', 'ONBEKEND')}")
        lines.append(f"QA/QC status: {validation_result.get('status', 'ONBEKEND')}")
        lines.append("")

        lines.append("3. PROJECTMAP")
        lines.append(f"Outputmap: {storage_result.get('project_output_dir', 'ONBEKEND')}")
        lines.append("")

        lines.append("4. AUTOMATISCHE BAOEES-WORKFLOW")
        lines.append("De projectanalyse is automatisch opgebouwd vanuit de BAOEES V3 workflow.")
        lines.append("De volgende onderdelen zijn conceptueel verwerkt:")
        lines.append("- projectselectie")
        lines.append("- projectconfiguratie")
        lines.append("- projectopslag")
        lines.append("- Digital Twin")
        lines.append("- bronregistratie")
        lines.append("- geotechniek")
        lines.append("- constructie")
        lines.append("- vergunningen")
        lines.append("- kosten")
        lines.append("- planning")
        lines.append("- verkeer en parkeren")
        lines.append("- riolering en afwatering")
        lines.append("- AERIUS/stikstof")
        lines.append("- GIS/kaartanalyse")
        lines.append("- hoeveelheden")
        lines.append("- bestek")
        lines.append("- aanbesteding")
        lines.append("- contract")
        lines.append("- uitvoering")
        lines.append("- oplevering")
        lines.append("- beheer en onderhoud")
        lines.append("- duurzaamheid")
        lines.append("- normen")
        lines.append("- learning")
        lines.append("- runtime orchestration")
        lines.append("")

        lines.append("5. OPMERKING")
        lines.append(
            "Dit rapport is automatisch gegenereerd als concept. "
            "Technische, juridische en inhoudelijke controle blijft noodzakelijk."
        )
        lines.append("")

        return "\n".join(lines)

    def write_basic_pdf(self, pdf_path, title, lines):
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            pdf_content = self.build_minimal_pdf(title=title, lines=lines)

            with open(pdf_path, "wb") as file:
                file.write(pdf_content)

            return {
                "path": str(pdf_path),
                "status": "OPGESLAGEN",
                "exists": pdf_path.exists(),
                "size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(pdf_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_minimal_pdf(self, title, lines):
        safe_lines = [title, ""] + lines

        pdf_lines = []
        pdf_lines.append("BT")
        pdf_lines.append("/F1 12 Tf")
        pdf_lines.append("50 790 Td")

        line_count = 0

        for line in safe_lines:
            if line_count > 48:
                break

            clean_line = (
                str(line)
                .replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )

            if clean_line.strip() == "":
                clean_line = " "

            pdf_lines.append(f"({clean_line[:95]}) Tj")
            pdf_lines.append("0 -15 Td")
            line_count += 1

        pdf_lines.append("ET")

        stream = "\n".join(pdf_lines).encode("latin-1", errors="replace")

        objects = []

        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        objects.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>\n"
            b"endobj\n"
        )
        objects.append(
            b"4 0 obj\n"
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            b"endobj\n"
        )
        objects.append(
            b"5 0 obj\n"
            + f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream\nendobj\n"
        )

        pdf = b"%PDF-1.4\n"
        offsets = [0]

        for obj in objects:
            offsets.append(len(pdf))
            pdf += obj

        xref_start = len(pdf)

        pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
        pdf += b"0000000000 65535 f \n"

        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

        pdf += (
            b"trailer\n"
            + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("latin-1")
            + b"startxref\n"
            + f"{xref_start}\n".encode("latin-1")
            + b"%%EOF\n"
        )

        return pdf

    def write_basic_docx(self, docx_path, title, lines):
        docx_path = Path(docx_path)
        docx_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            document_xml = self.build_document_xml(title=title, lines=lines)

            with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as docx:
                docx.writestr("[Content_Types].xml", self.content_types_xml())
                docx.writestr("_rels/.rels", self.root_rels_xml())
                docx.writestr("word/document.xml", document_xml)
                docx.writestr("word/_rels/document.xml.rels", self.document_rels_xml())

            return {
                "path": str(docx_path),
                "status": "OPGESLAGEN",
                "exists": docx_path.exists(),
                "size_bytes": docx_path.stat().st_size if docx_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(docx_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_document_xml(self, title, lines):
        paragraphs = []

        paragraphs.append(self.docx_paragraph(title, bold=True))

        for line in lines:
            paragraphs.append(self.docx_paragraph(line))

        body = "\n".join(paragraphs)

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>'''

    def docx_paragraph(self, text, bold=False):
        text = html.escape(str(text))

        if bold:
            return f'''
    <w:p>
      <w:r>
        <w:rPr><w:b/></w:rPr>
        <w:t>{text}</w:t>
      </w:r>
    </w:p>'''

        return f'''
    <w:p>
      <w:r>
        <w:t>{text}</w:t>
      </w:r>
    </w:p>'''

    def content_types_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

    def root_rels_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>'''

    def document_rels_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''

    def build_warnings(self, pdf_result, docx_result):
        warnings = []

        if pdf_result.get("status") != "OPGESLAGEN":
            warnings.append("PDF-rapport is niet opgeslagen.")

        if docx_result.get("status") != "OPGESLAGEN":
            warnings.append("DOCX-rapport is niet opgeslagen.")

        if not warnings:
            warnings.append("Geen kritieke PDF/DOCX-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PDF_DOCX_REPORT_EXPORT_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste echte PDF/DOCX-exportlaag. "
                "De volgende stap is professionele rapportopmaak met inhoudsopgave, tabellen, "
                "hoofdstukken, figuren en projectbijlagen."
            ),
            "next_steps": [
                "ProjectPdfDocxWriterEngine koppelen aan BAOEES Core",
                "PDF/DOCX opnemen in ZIP-export",
                "rapportinhoud per discipline uitbreiden",
                "voorblad en inhoudsopgave toevoegen",
                "professionele huisstijl toevoegen",
                "tabellen en bijlagen toevoegen"
            ]
        }

    def get_pdf_docx_result(self):
        return self.pdf_docx_result

    def run(self):
        print("PDF/DOCX Report Export Engine actief")