"""JSON, CSV and dependency-free XLSX exporters for BB20."""

from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import QuantityTakeoffReport


class QuantityTakeoffExporter:
    def export_json(
        self,
        report: QuantityTakeoffReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return path

    def export_csv(
        self,
        report: QuantityTakeoffReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "quantity_id",
            "source_object_id",
            "source_model",
            "source_level_id",
            "category",
            "work_section",
            "material",
            "quantity_type",
            "value",
            "unit",
            "basis",
            "status",
            "formula",
            "inputs",
            "assumptions",
            "drawing_refs",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for record in report.records:
                data = record.to_dict()
                writer.writerow(
                    {
                        key: (
                            json.dumps(data[key], ensure_ascii=False, sort_keys=True)
                            if isinstance(data.get(key), (dict, list))
                            else data.get(key)
                        )
                        for key in fieldnames
                    }
                )
        return path

    def export_xlsx(
        self,
        report: QuantityTakeoffReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        quantity_headers = [
            "Quantity ID",
            "Source Object",
            "Source Model",
            "Level",
            "Category",
            "Work Section",
            "Material",
            "Quantity Type",
            "Value",
            "Unit",
            "Basis",
            "Status",
            "Formula",
            "Inputs",
            "Assumptions",
            "Drawing Refs",
        ]
        quantity_rows: list[list[Any]] = [quantity_headers]
        for record in report.records:
            data = record.to_dict()
            quantity_rows.append(
                [
                    data["quantity_id"],
                    data["source_object_id"],
                    data["source_model"],
                    data["source_level_id"] or "",
                    data["category"],
                    data["work_section"],
                    data["material"] or "",
                    data["quantity_type"],
                    data["value"],
                    data["unit"],
                    data["basis"],
                    data["status"],
                    data["formula"],
                    json.dumps(data["inputs"], ensure_ascii=False, sort_keys=True),
                    "; ".join(data["assumptions"]),
                    "; ".join(data["drawing_refs"]),
                ]
            )

        summary_rows: list[list[Any]] = [
            ["PROJECT-PHOENIX BB20 Quantity Take-Off"],
            ["Project ID", report.project_id],
            ["Engine version", report.engine_version],
            ["Model fingerprint", report.model_fingerprint_sha256],
            ["Record count", len(report.records)],
            ["Issue count", len(report.issues)],
            [],
            ["Totals by work section"],
            ["Work Section", "Unit", "Value"],
        ]
        for section, units in report.totals_by_work_section.items():
            for unit, value in units.items():
                summary_rows.append([section, unit, value])

        summary_rows.extend([[], ["Totals by material"], ["Material", "Unit", "Value"]])
        for material, units in report.totals_by_material.items():
            for unit, value in units.items():
                summary_rows.append([material, unit, value])

        summary_rows.extend([[], ["Issues"], ["Code", "Severity", "Object", "Message"]])
        for issue in report.issues:
            summary_rows.append(
                [
                    issue.code,
                    issue.severity,
                    issue.source_object_id or "",
                    issue.message,
                ]
            )

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_relationships_xml())
            archive.writestr("docProps/core.xml", self._core_properties_xml())
            archive.writestr("docProps/app.xml", self._app_properties_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                self._workbook_relationships_xml(),
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                self._worksheet_xml(quantity_rows),
            )
            archive.writestr(
                "xl/worksheets/sheet2.xml",
                self._worksheet_xml(summary_rows),
            )
        return path

    @staticmethod
    def _cell_reference(column_index: int, row_index: int) -> str:
        letters = ""
        value = column_index
        while value:
            value, remainder = divmod(value - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row_index}"

    def _worksheet_xml(self, rows: list[list[Any]]) -> str:
        xml_rows: list[str] = []
        for row_index, row in enumerate(rows, start=1):
            cells: list[str] = []
            for column_index, value in enumerate(row, start=1):
                reference = self._cell_reference(column_index, row_index)
                if isinstance(value, bool):
                    cells.append(f'<c r="{reference}" t="b"><v>{int(value)}</v></c>')
                elif isinstance(value, (int, float)):
                    cells.append(f'<c r="{reference}"><v>{value}</v></c>')
                else:
                    text = escape("" if value is None else str(value))
                    cells.append(
                        f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>'
                    )
            xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            '</worksheet>'
        )

    @staticmethod
    def _content_types_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _root_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _workbook_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            '<sheet name="Quantities" sheetId="1" r:id="rId1"/>'
            '<sheet name="Summary" sheetId="2" r:id="rId2"/>'
            '</sheets>'
            '</workbook>'
        )

    @staticmethod
    def _workbook_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _core_properties_xml() -> str:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            '<dc:title>BB20 Quantity Take-Off</dc:title>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _app_properties_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>PROJECT-PHOENIX</Application>'
            '</Properties>'
        )
