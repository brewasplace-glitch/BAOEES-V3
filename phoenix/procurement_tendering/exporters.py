"""Dependency-free BB25 procurement workbook, tender documents and dossier."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import textwrap
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import ProcurementReport, TenderLine


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class ProcurementTenderingExporter:
    def export_all(self, report: ProcurementReport, output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "json": self.export_json(report, root / "procurement_report.json"),
            "packages_csv": self._write_records(
                root / "procurement_packages.csv",
                [item.to_dict() for item in report.packages],
                [
                    "package_id", "title", "work_section", "currency",
                    "benchmark_budget", "planned_start_date", "planned_finish_date",
                    "status", "scope", "tender_line_ids", "qualification_requirements",
                ],
            ),
            "lines_csv": self._write_records(
                root / "tender_lines.csv",
                [item.to_dict() for item in report.tender_lines],
                [
                    "line_id", "package_id", "quantity_id", "description",
                    "work_section", "quantity", "unit", "benchmark_unit_rate",
                    "benchmark_total", "required_by_date", "source_object_ids",
                ],
            ),
            "suppliers_csv": self._write_records(
                root / "supplier_register.csv",
                [item.to_dict() for item in report.suppliers],
                [
                    "supplier_id", "supplier_name", "contact_name", "email",
                    "country", "approved", "categories",
                ],
            ),
            "bids_csv": self._write_records(
                root / "bid_comparison.csv",
                [item.to_dict() for item in report.evaluations],
                [
                    "package_id", "bid_id", "supplier_id", "supplier_name",
                    "currency", "offered_total", "missing_line_allowance",
                    "evaluated_total", "included_line_count", "expected_line_count",
                    "completeness_score", "price_score", "delivery_score",
                    "delivery_workdays", "responsive", "deviation_count",
                    "missing_line_ids", "extra_line_ids", "exclusions",
                ],
            ),
            "awards_csv": self._write_records(
                root / "award_recommendations.csv",
                [item.to_dict() for item in report.recommendations],
                [
                    "package_id", "scenario_id", "scenario_name",
                    "recommended_bid_id", "recommended_supplier_id",
                    "recommended_supplier_name", "evaluated_total", "weighted_score",
                    "status", "rationale",
                ],
            ),
            "xlsx": self.export_xlsx(report, root / "procurement_tendering_workbook.xlsx"),
            "docx": self.export_docx(report, root / "request_for_tender.docx"),
            "pdf": self.export_pdf(report, root / "request_for_tender.pdf"),
        }
        paths["checksums"] = self.export_checksums(paths, root / "checksums.sha256")
        paths["dossier"] = self.export_dossier_zip(
            report, paths, root / "procurement_tender_dossier.zip"
        )
        return paths

    def export_json(self, report: ProcurementReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_records(
        output_path: str | Path,
        records: list[dict[str, Any]],
        fields: list[str],
    ) -> Path:
        path = Path(output_path)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in records:
                writer.writerow({
                    field: (
                        json.dumps(record.get(field), ensure_ascii=False, sort_keys=True)
                        if isinstance(record.get(field), (dict, list))
                        else record.get(field)
                    )
                    for field in fields
                })
        return path

    def export_xlsx(self, report: ProcurementReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        summary = [
            ["PROJECT-PHOENIX BB25 Procurement & Tendering"],
            ["Project ID", report.project_id],
            ["Project name", report.project_name],
            ["Currency", report.currency],
            ["Procurement passed", report.procurement_passed],
            ["Benchmark budget", report.benchmark_budget_total],
            ["Package count", len(report.packages)],
            ["Supplier count", len(report.suppliers)],
            ["Bid count", len(report.bids)],
            [],
            ["Award scenarios"],
            ["Scenario", "Package", "Recommended supplier", "Evaluated total", "Score"],
        ]
        summary.extend([
            [
                item.scenario_name,
                item.package_id,
                item.recommended_supplier_name or "",
                item.evaluated_total,
                item.weighted_score,
            ]
            for item in report.recommendations
        ])
        packages = [[
            "Package ID", "Title", "Work Section", "Budget", "Currency",
            "Start", "Finish", "Status", "Scope",
        ]] + [[
            item.package_id, item.title, item.work_section, item.benchmark_budget,
            item.currency, item.planned_start_date or "", item.planned_finish_date or "",
            item.status, item.scope,
        ] for item in report.packages]
        lines = [[
            "Line ID", "Package ID", "Quantity ID", "Description", "Quantity",
            "Unit", "Benchmark unit rate", "Benchmark total", "Required by",
        ]] + [[
            item.line_id, item.package_id, item.quantity_id, item.description,
            item.quantity, item.unit, item.benchmark_unit_rate, item.benchmark_total,
            item.required_by_date or "",
        ] for item in report.tender_lines]
        bids = [[
            "Package", "Bid", "Supplier", "Currency", "Offered total",
            "Missing allowance", "Evaluated total", "Completeness", "Price score",
            "Delivery score", "Delivery days", "Responsive", "Deviations",
        ]] + [[
            item.package_id, item.bid_id, item.supplier_name, item.currency,
            item.offered_total, item.missing_line_allowance, item.evaluated_total,
            item.completeness_score, item.price_score, item.delivery_score,
            item.delivery_workdays, item.responsive, item.deviation_count,
        ] for item in report.evaluations]
        suppliers = [[
            "Supplier ID", "Supplier name", "Contact", "Email", "Country",
            "Approved", "Categories",
        ]] + [[
            item.supplier_id, item.supplier_name, item.contact_name, item.email,
            item.country, item.approved, "; ".join(item.categories),
        ] for item in report.suppliers]
        sheets = [
            ("Summary", summary),
            ("Packages", packages),
            ("Tender Lines", lines),
            ("Bid Comparison", bids),
            ("Suppliers", suppliers),
        ]
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            self._zip_write(archive, "[Content_Types].xml", self._xlsx_content_types(len(sheets)))
            self._zip_write(archive, "_rels/.rels", self._xlsx_root_rels())
            self._zip_write(archive, "docProps/core.xml", self._xlsx_core(report))
            self._zip_write(archive, "docProps/app.xml", self._xlsx_app())
            self._zip_write(archive, "xl/workbook.xml", self._xlsx_workbook(sheets))
            self._zip_write(archive, "xl/_rels/workbook.xml.rels", self._xlsx_rels(len(sheets)))
            self._zip_write(archive, "xl/styles.xml", self._xlsx_styles())
            for index, (_, rows) in enumerate(sheets, start=1):
                headers = {1, 11, 12} if index == 1 else {1}
                self._zip_write(
                    archive,
                    f"xl/worksheets/sheet{index}.xml",
                    self._worksheet_xml(rows, headers, summary=(index == 1)),
                )
        return path

    def export_docx(self, report: ProcurementReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        paragraphs = self._document_paragraphs(report)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            self._zip_write(archive, "[Content_Types].xml", self._docx_content_types())
            self._zip_write(archive, "_rels/.rels", self._docx_root_rels())
            self._zip_write(archive, "docProps/core.xml", self._docx_core(report))
            self._zip_write(archive, "docProps/app.xml", self._docx_app())
            self._zip_write(archive, "word/document.xml", self._docx_document(paragraphs))
            self._zip_write(archive, "word/styles.xml", self._docx_styles())
            self._zip_write(archive, "word/_rels/document.xml.rels", self._empty_rels())
        return path

    def export_pdf(self, report: ProcurementReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.write_bytes(self._build_pdf(self._plain_text_lines(report)))
        return path

    def export_checksums(self, paths: dict[str, Path], output_path: str | Path) -> Path:
        path = Path(output_path)
        lines = [
            f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}"
            for key, source in sorted(paths.items())
            if key not in {"checksums", "dossier"}
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_dossier_zip(
        self,
        report: ProcurementReport,
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for key, source in sorted(paths.items()):
                if key != "dossier":
                    self._zip_write_bytes(archive, source.name, source.read_bytes())
            self._zip_write(
                archive,
                "PACKAGE_README.txt",
                (
                    "PROJECT-PHOENIX BB25 PROCUREMENT & TENDERING DOSSIER\n"
                    f"Project: {report.project_name} ({report.project_id})\n"
                    f"Currency: {report.currency}\n"
                    f"Packages: {len(report.packages)}\n"
                    "Recommendations require technical, legal and commercial review.\n"
                    "No automatic contract award is performed.\n"
                ),
            )
        return path

    def _document_paragraphs(self, report: ProcurementReport) -> list[tuple[str, str]]:
        paragraphs: list[tuple[str, str]] = [
            ("Title", report.project_name),
            ("Subtitle", "Request for Tender"),
            ("Normal", f"Project ID: {report.project_id}"),
            ("Normal", f"Currency: {report.currency}"),
            (
                "Normal",
                "Tenderers shall price the full scope and list qualifications, exclusions, proposed durations and payment terms. Automatic currency conversion is not used.",
            ),
            ("Heading1", "Tender instructions"),
            ("ListParagraph", "Submit a priced line schedule using the issued tender line IDs."),
            ("ListParagraph", "Identify every omission, exclusion, alternative and commercial qualification."),
            ("ListParagraph", "Confirm bid validity, delivery duration, resources and programme."),
            ("ListParagraph", "Award recommendations remain subject to professional review and approval."),
        ]
        lines_by_package: dict[str, list[TenderLine]] = {}
        for line in report.tender_lines:
            lines_by_package.setdefault(line.package_id, []).append(line)
        for package in report.packages:
            paragraphs.extend([
                ("Heading1", f"{package.package_id} - {package.title}"),
                ("Normal", package.scope),
                ("Normal", f"Benchmark budget: {package.currency} {package.benchmark_budget:,.2f}"),
                (
                    "Normal",
                    f"Planned period: {package.planned_start_date or 'not set'} to {package.planned_finish_date or 'not set'}",
                ),
                ("Heading2", "Pricing schedule"),
            ])
            for line in lines_by_package.get(package.package_id, []):
                paragraphs.append((
                    "ListParagraph",
                    f"{line.line_id} | {line.description} | {line.quantity:g} {line.unit} | Quantity source {line.quantity_id}",
                ))
            paragraphs.append(("Heading2", "Minimum submission requirements"))
            for requirement in package.qualification_requirements:
                paragraphs.append(("ListParagraph", requirement))
        paragraphs.extend([
            ("Heading1", "Evaluation method"),
            (
                "Normal",
                "Phoenix normalizes bid totals, adds benchmark allowances for omitted lines, identifies extra lines and exclusions, and compares price, completeness and delivery.",
            ),
            ("ListParagraph", "Lowest evaluated cost: price 80%, completeness 15%, delivery 5%."),
            ("ListParagraph", "Balanced award: price 55%, completeness 30%, delivery 15%."),
            ("ListParagraph", "Schedule priority: price 35%, completeness 20%, delivery 45%."),
        ])
        return paragraphs

    def _plain_text_lines(self, report: ProcurementReport) -> list[str]:
        lines: list[str] = []
        for style, paragraph in self._document_paragraphs(report):
            text = paragraph.upper() if style in {"Title", "Heading1"} else paragraph
            lines.extend(
                textwrap.wrap(
                    self._ascii(text),
                    width=92,
                    subsequent_indent="  " if style == "ListParagraph" else "",
                ) or [""]
            )
            if style in {"Title", "Subtitle", "Heading1", "Heading2"}:
                lines.append("")
        return lines

    @staticmethod
    def _ascii(value: str) -> str:
        for source, target in {
            "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"',
        }.items():
            value = value.replace(source, target)
        return value.encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def _zip_write(archive: zipfile.ZipFile, name: str, text: str) -> None:
        ProcurementTenderingExporter._zip_write_bytes(archive, name, text.encode("utf-8"))

    @staticmethod
    def _zip_write_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)

    @staticmethod
    def _cell_ref(column: int, row: int) -> str:
        letters = ""
        while column:
            column, remainder = divmod(column - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row}"

    def _worksheet_xml(self, rows: list[list[Any]], header_rows: set[int], summary: bool = False) -> str:
        xml_rows: list[str] = []
        max_columns = max((len(row) for row in rows), default=1)
        for row_number, row in enumerate(rows, start=1):
            style = 1 if row_number in header_rows else 0
            cells: list[str] = []
            for column_number, value in enumerate(row, start=1):
                ref = self._cell_ref(column_number, row_number)
                if isinstance(value, bool):
                    cells.append(f'<c r="{ref}" s="{style}" t="b"><v>{int(value)}</v></c>')
                elif isinstance(value, (int, float)):
                    cells.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
                else:
                    cells.append(
                        f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>'
                        f'{escape("" if value is None else str(value))}</t></is></c>'
                    )
            xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
        def column_width(index: int) -> int:
            if summary and index == 1:
                return 56
            if index in {2, 3, 9}:
                return 40
            return 20

        columns = "".join(
            f'<col min="{index}" max="{index}" width="{column_width(index)}" customWidth="1"/>'
            for index in range(1, max_columns + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>'
            f'<cols>{columns}</cols>'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            '<pageMargins left="0.25" right="0.25" top="0.35" bottom="0.35" header="0.15" footer="0.15"/>'
            '<pageSetup paperSize="9" orientation="landscape" fitToWidth="1" fitToHeight="0"/>'
            '</worksheet>'
        )

    @staticmethod
    def _xlsx_content_types(sheet_count: int) -> str:
        sheets = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            f'{sheets}'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _xlsx_root_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _xlsx_workbook(sheets: list[tuple[str, list[list[Any]]]]) -> str:
        body = "".join(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, (name, _) in enumerate(sheets, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{body}</sheets></workbook>'
        )

    @staticmethod
    def _xlsx_rels(sheet_count: int) -> str:
        relationships = "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{relationships}'
            f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _xlsx_styles() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font></fonts>'
            '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>'
        )

    @staticmethod
    def _xlsx_core(report: ProcurementReport) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            f'<dc:title>{escape(report.project_name)} procurement workbook</dc:title>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:created>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _xlsx_app() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>PROJECT-PHOENIX</Application></Properties>'
        )

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
    def _docx_core(report: ProcurementReport) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            f'<dc:title>{escape(report.project_name)} Request for Tender</dc:title>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:created>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _docx_app() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>PROJECT-PHOENIX</Application></Properties>'
        )

    def _docx_document(self, paragraphs: list[tuple[str, str]]) -> str:
        body: list[str] = []
        for style, text in paragraphs:
            style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
            cleaned = escape(re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text))
            body.append(
                f'<w:p>{style_xml}<w:r><w:t xml:space="preserve">{cleaned}</w:t></w:r></w:p>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            + "".join(body)
            + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000"/></w:sectPr></w:body></w:document>'
        )

    @staticmethod
    def _docx_styles() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:rPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="100" w:line="270" w:lineRule="auto"/></w:pPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:i/><w:sz w:val="24"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360" w:hanging="180"/></w:pPr></w:style>'
            '</w:styles>'
        )

    @staticmethod
    def _empty_rels() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )

    def _build_pdf(self, lines: list[str]) -> bytes:
        page_width, page_height, left, top, font_size, leading = 595, 842, 44, 800, 8, 11
        pages = [lines[index:index + 64] for index in range(0, len(lines), 64)] or [[]]
        objects: dict[int, bytes] = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        }
        kids: list[str] = []
        for index, page_lines in enumerate(pages):
            page_id = 4 + index * 2
            content_id = page_id + 1
            kids.append(f"{page_id} 0 R")
            content = ["BT", f"/F1 {font_size} Tf", f"{left} {top} Td", f"{leading} TL"]
            for line in page_lines:
                safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                content.extend([f"({safe}) Tj", "T*"])
            content.append("ET")
            stream = "\n".join(content).encode("latin-1")
            objects[content_id] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"\nendstream"
            )
            objects[page_id] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode("ascii")
        max_id = max(objects)
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (max_id + 1)
        for object_id in range(1, max_id + 1):
            offsets[object_id] = len(output)
            output.extend(f"{object_id} 0 obj\n".encode("ascii"))
            output.extend(objects[object_id])
            output.extend(b"\nendobj\n")
        xref = len(output)
        output.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for object_id in range(1, max_id + 1):
            output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
        output.extend(
            f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        return bytes(output)
