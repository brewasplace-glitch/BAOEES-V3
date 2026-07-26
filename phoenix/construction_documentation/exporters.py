"""Dependency-free BB23 JSON, CSV, Markdown, HTML, DOCX, PDF and ZIP exports."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import textwrap
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import ConstructionDocumentPackage


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class ConstructionDocumentationExporter:
    """Publish a controlled BB23 construction-documentation dossier."""

    def export_all(
        self,
        package: ConstructionDocumentPackage,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)

        paths = {
            "manifest": self.export_json(
                package,
                root / "construction_documentation_manifest.json",
            ),
            "register": self.export_register_csv(
                package,
                root / "document_register.csv",
            ),
            "markdown": self.export_markdown(
                package,
                root / "technical_project_report.md",
            ),
            "html": self.export_html(
                package,
                root / "technical_project_report.html",
            ),
            "docx": self.export_docx(
                package,
                root / "technical_project_report.docx",
            ),
            "pdf": self.export_pdf(
                package,
                root / "technical_project_report.pdf",
            ),
        }

        paths["checksums"] = self.export_checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self.export_dossier_zip(
            package,
            paths,
            root / "construction_documentation_dossier.zip",
        )
        return paths

    def export_json(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                package.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def export_register_csv(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "document_id",
            "title",
            "document_type",
            "revision",
            "status",
            "filename",
            "discipline",
            "source_refs",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in package.document_register:
                data = record.to_dict()
                writer.writerow(
                    {
                        field: (
                            "; ".join(data[field])
                            if isinstance(data.get(field), list)
                            else data.get(field)
                        )
                        for field in fields
                    }
                )
        return path

    def export_markdown(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._markdown(package),
            encoding="utf-8",
        )
        return path

    def export_html(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._html(package),
            encoding="utf-8",
        )
        return path

    def export_docx(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        paragraphs = self._document_paragraphs(package)
        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            self._zip_write(
                archive,
                "[Content_Types].xml",
                self._docx_content_types(),
            )
            self._zip_write(
                archive,
                "_rels/.rels",
                self._docx_root_rels(),
            )
            self._zip_write(
                archive,
                "docProps/core.xml",
                self._docx_core_properties(package),
            )
            self._zip_write(
                archive,
                "docProps/app.xml",
                self._docx_app_properties(),
            )
            self._zip_write(
                archive,
                "word/document.xml",
                self._docx_document_xml(paragraphs),
            )
            self._zip_write(
                archive,
                "word/styles.xml",
                self._docx_styles_xml(),
            )
            self._zip_write(
                archive,
                "word/_rels/document.xml.rels",
                self._docx_document_rels(),
            )
        return path

    def export_pdf(
        self,
        package: ConstructionDocumentPackage,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = self._plain_text_lines(package)
        path.write_bytes(self._build_pdf(lines))
        return path

    def export_checksums(
        self,
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        lines: list[str] = []
        for key, source in sorted(paths.items()):
            if key in {"checksums", "dossier"}:
                continue
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            lines.append(f"{digest}  {source.name}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_dossier_zip(
        self,
        package: ConstructionDocumentPackage,
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for key, source in sorted(paths.items()):
                if key == "dossier":
                    continue
                self._zip_write_bytes(
                    archive,
                    source.name,
                    source.read_bytes(),
                )
            self._zip_write(
                archive,
                "PACKAGE_README.txt",
                (
                    "PROJECT-PHOENIX BB23 CONSTRUCTION DOCUMENTATION DOSSIER\n"
                    f"Project: {package.project_name} ({package.project_id})\n"
                    f"Revision: {package.revision}\n"
                    f"Stage: {package.stage}\n"
                    f"Status: {package.status.value}\n"
                    "This package is non-certifying until professionally "
                    "reviewed and approved.\n"
                ),
            )
        return path

    def _markdown(
        self,
        package: ConstructionDocumentPackage,
    ) -> str:
        lines = [
            f"# {package.project_name}",
            "",
            "## Construction documentation package",
            "",
            f"- Project ID: `{package.project_id}`",
            f"- Package ID: `{package.package_id}`",
            f"- Revision: `{package.revision}`",
            f"- Stage: `{package.stage}`",
            f"- Status: `{package.status.value}`",
            "",
        ]
        for section in package.sections:
            lines.extend([f"## {section.title}", ""])
            for paragraph in section.paragraphs:
                lines.extend([paragraph, ""])
            for entry in section.entries:
                lines.append(
                    "- "
                    + "; ".join(
                        f"{key}: {self._display_value(value)}"
                        for key, value in entry.items()
                    )
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _html(
        self,
        package: ConstructionDocumentPackage,
    ) -> str:
        sections: list[str] = []
        for section in package.sections:
            paragraphs = "".join(
                f"<p>{html.escape(paragraph)}</p>"
                for paragraph in section.paragraphs
            )
            entries = ""
            if section.entries:
                rows = "".join(
                    "<tr>"
                    + "".join(
                        (
                            f"<th>{html.escape(str(key))}</th>"
                            f"<td>{html.escape(self._display_value(value))}</td>"
                        )
                        for key, value in entry.items()
                    )
                    + "</tr>"
                    for entry in section.entries
                )
                entries = f"<table>{rows}</table>"
            sections.append(
                f"<section><h2>{html.escape(section.title)}</h2>"
                f"{paragraphs}{entries}</section>"
            )

        return (
            "<!doctype html><html lang=\"en\"><head>"
            "<meta charset=\"utf-8\">"
            f"<title>{html.escape(package.project_name)}</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;max-width:1000px;"
            "margin:40px auto;line-height:1.45;color:#222}"
            "h1{border-bottom:3px solid #222;padding-bottom:8px}"
            "h2{margin-top:30px;border-bottom:1px solid #999}"
            "table{border-collapse:collapse;width:100%;margin:12px 0}"
            "th,td{border:1px solid #bbb;padding:6px;text-align:left;"
            "vertical-align:top}"
            "th{background:#eee;width:22%}"
            ".control{padding:12px;background:#f4f4f4;border:1px solid #bbb}"
            "</style></head><body>"
            f"<h1>{html.escape(package.project_name)}</h1>"
            "<div class=\"control\">"
            f"<strong>Project:</strong> {html.escape(package.project_id)}<br>"
            f"<strong>Package:</strong> {html.escape(package.package_id)}<br>"
            f"<strong>Revision:</strong> {html.escape(package.revision)}<br>"
            f"<strong>Stage:</strong> {html.escape(package.stage)}<br>"
            f"<strong>Status:</strong> {html.escape(package.status.value)}"
            "</div>"
            + "".join(sections)
            + "</body></html>"
        )

    def _document_paragraphs(
        self,
        package: ConstructionDocumentPackage,
    ) -> list[tuple[str, str]]:
        paragraphs: list[tuple[str, str]] = [
            ("Title", package.project_name),
            ("Subtitle", "Construction documentation package"),
            ("Normal", f"Project ID: {package.project_id}"),
            ("Normal", f"Package ID: {package.package_id}"),
            ("Normal", f"Revision: {package.revision}"),
            ("Normal", f"Stage: {package.stage}"),
            ("Normal", f"Status: {package.status.value}"),
        ]
        for section in package.sections:
            paragraphs.append(("Heading1", section.title))
            for paragraph in section.paragraphs:
                paragraphs.append(("Normal", paragraph))
            for entry in section.entries:
                text = "; ".join(
                    f"{key}: {self._display_value(value)}"
                    for key, value in entry.items()
                )
                paragraphs.append(("ListParagraph", text))
        return paragraphs

    def _plain_text_lines(
        self,
        package: ConstructionDocumentPackage,
    ) -> list[str]:
        lines = [
            package.project_name.upper(),
            "CONSTRUCTION DOCUMENTATION PACKAGE",
            "",
            f"Project ID: {package.project_id}",
            f"Package ID: {package.package_id}",
            f"Revision: {package.revision}",
            f"Stage: {package.stage}",
            f"Status: {package.status.value}",
            "",
        ]
        for section in package.sections:
            lines.extend([section.title.upper(), ""])
            for paragraph in section.paragraphs:
                lines.extend(
                    textwrap.wrap(
                        self._ascii_text(paragraph),
                        width=92,
                    )
                    or [""]
                )
                lines.append("")
            for entry in section.entries:
                text = "; ".join(
                    f"{key}: {self._display_value(value)}"
                    for key, value in entry.items()
                )
                wrapped = textwrap.wrap(
                    self._ascii_text("- " + text),
                    width=92,
                    subsequent_indent="  ",
                )
                lines.extend(wrapped or ["-"])
            lines.append("")
        return lines

    @staticmethod
    def _display_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
            )
        return str(value)

    @staticmethod
    def _ascii_text(value: str) -> str:
        replacements = {
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "-",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return value.encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def _zip_write(
        archive: zipfile.ZipFile,
        name: str,
        text: str,
    ) -> None:
        ConstructionDocumentationExporter._zip_write_bytes(
            archive,
            name,
            text.encode("utf-8"),
        )

    @staticmethod
    def _zip_write_bytes(
        archive: zipfile.ZipFile,
        name: str,
        data: bytes,
    ) -> None:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)

    @staticmethod
    def _docx_content_types() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _docx_root_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _docx_core_properties(
        package: ConstructionDocumentPackage,
    ) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            f'<dc:title>{escape(package.project_name)}</dc:title>'
            f'<dc:subject>BB23 revision {escape(package.revision)}</dc:subject>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:modified>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _docx_app_properties() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties '
            'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>PROJECT-PHOENIX</Application>'
            '</Properties>'
        )

    def _docx_document_xml(
        self,
        paragraphs: list[tuple[str, str]],
    ) -> str:
        body: list[str] = []
        for style, text in paragraphs:
            cleaned = self._xml_text(text)
            style_xml = (
                f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
                if style
                else ""
            )
            body.append(
                f'<w:p>{style_xml}<w:r><w:t xml:space="preserve">'
                f'{cleaned}</w:t></w:r></w:p>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            + "".join(body)
            + '<w:sectPr>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>'
            '</w:sectPr>'
            '</w:body></w:document>'
        )

    @staticmethod
    def _xml_text(value: str) -> str:
        value = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(value))
        return escape(value)

    @staticmethod
    def _docx_styles_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:docDefaults><w:rPrDefault><w:rPr>'
            '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
            '<w:sz w:val="20"/>'
            '</w:rPr></w:rPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:qFormat/>'
            '<w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Title">'
            '<w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>'
            '<w:pPr><w:spacing w:after="180"/></w:pPr>'
            '<w:rPr><w:b/><w:sz w:val="36"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Subtitle">'
            '<w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="240"/></w:pPr>'
            '<w:rPr><w:i/><w:sz w:val="24"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1">'
            '<w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>'
            '<w:pPr><w:keepNext/><w:spacing w:before="260" w:after="120"/></w:pPr>'
            '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="ListParagraph">'
            '<w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:ind w:left="360" w:hanging="180"/></w:pPr>'
            '</w:style>'
            '</w:styles>'
        )

    @staticmethod
    def _docx_document_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )

    def _build_pdf(self, lines: list[str]) -> bytes:
        page_width = 595
        page_height = 842
        left = 48
        top = 798
        font_size = 9
        leading = 12
        lines_per_page = 58

        pages = [
            lines[index:index + lines_per_page]
            for index in range(0, len(lines), lines_per_page)
        ] or [[]]

        objects: dict[int, bytes] = {}
        catalog_id = 1
        pages_id = 2
        font_id = 3
        kids: list[str] = []

        objects[catalog_id] = (
            b"<< /Type /Catalog /Pages 2 0 R >>"
        )
        objects[font_id] = (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        )

        for page_index, page_lines in enumerate(pages):
            page_id = 4 + page_index * 2
            content_id = page_id + 1
            kids.append(f"{page_id} 0 R")

            content_parts = [
                "BT",
                f"/F1 {font_size} Tf",
                f"{left} {top} Td",
                f"{leading} TL",
            ]
            for line in page_lines:
                safe = self._pdf_escape(self._ascii_text(line))
                content_parts.append(f"({safe}) Tj")
                content_parts.append("T*")
            content_parts.append("ET")
            stream = "\n".join(content_parts).encode("latin-1")

            objects[content_id] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"\nendstream"
            )
            objects[page_id] = (
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R "
                    f"/MediaBox [0 0 {page_width} {page_height}] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii")
            )

        objects[pages_id] = (
            (
                f"<< /Type /Pages /Kids [{' '.join(kids)}] "
                f"/Count {len(pages)} >>"
            ).encode("ascii")
        )

        max_id = max(objects)
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (max_id + 1)

        for object_id in range(1, max_id + 1):
            offsets[object_id] = len(output)
            output.extend(f"{object_id} 0 obj\n".encode("ascii"))
            output.extend(objects[object_id])
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for object_id in range(1, max_id + 1):
            output.extend(
                f"{offsets[object_id]:010d} 00000 n \n".encode("ascii")
            )

        output.extend(
            (
                f"trailer\n<< /Size {max_id + 1} /Root {catalog_id} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(output)

    @staticmethod
    def _pdf_escape(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
