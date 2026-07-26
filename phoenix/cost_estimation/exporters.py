"""JSON, CSV and dependency-free XLSX exporters for BB21."""

from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import CostEstimateReport


class CostEstimateExporter:
    def export_json(self, report: CostEstimateReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def export_csv(self, report: CostEstimateReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "line_id",
            "scenario_id",
            "quantity_id",
            "source_object_id",
            "source_model",
            "source_level_id",
            "category",
            "work_section",
            "material",
            "quantity_type",
            "cost_code",
            "description",
            "rate_item_id",
            "base_quantity",
            "waste_percent",
            "priced_quantity",
            "unit",
            "base_unit_rate",
            "adjusted_unit_rate",
            "material_cost",
            "labor_cost",
            "equipment_cost",
            "subcontract_cost",
            "other_cost",
            "direct_cost",
            "currency",
            "drawing_refs",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for scenario in report.scenarios:
                for line in scenario.lines:
                    data = line.to_dict()
                    writer.writerow(
                        {
                            key: (
                                "; ".join(data[key])
                                if key == "drawing_refs"
                                else data.get(key)
                            )
                            for key in fields
                        }
                    )
        return path

    def export_xlsx(self, report: CostEstimateReport, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        summary_rows: list[list[Any]] = [
            ["PROJECT-PHOENIX BB21 Cost Estimate"],
            ["Project ID", report.project_id],
            ["Currency", report.currency],
            ["Price date", report.price_date],
            ["Jurisdiction", report.jurisdiction],
            ["Location profile", report.location_profile],
            ["Rate book", report.ratebook_id],
            ["Rate-book version", report.ratebook_version],
            ["Rate-book status", report.ratebook_status],
            [],
            [
                "Scenario",
                "Direct",
                "Overhead",
                "Risk",
                "Contingency",
                "Profit",
                "Pre-tax",
                "Tax",
                "Total",
                "Currency",
            ],
        ]
        for estimate in report.scenarios:
            summary_rows.append(
                [
                    estimate.scenario.name,
                    estimate.direct_cost,
                    estimate.overhead_cost,
                    estimate.risk_cost,
                    estimate.contingency_cost,
                    estimate.profit_cost,
                    estimate.pre_tax_cost,
                    estimate.tax_cost,
                    estimate.total_cost,
                    estimate.scenario.currency,
                ]
            )

        line_headers = [
            "Scenario",
            "Line ID",
            "Quantity ID",
            "Source Object",
            "Level",
            "Work Section",
            "Material",
            "Quantity Type",
            "Cost Code",
            "Description",
            "Base Quantity",
            "Waste %",
            "Priced Quantity",
            "Unit",
            "Base Unit Rate",
            "Adjusted Unit Rate",
            "Material Cost",
            "Labor Cost",
            "Equipment Cost",
            "Subcontract Cost",
            "Other Cost",
            "Direct Cost",
            "Currency",
            "Drawing Refs",
        ]
        line_rows: list[list[Any]] = [line_headers]
        for estimate in report.scenarios:
            for line in estimate.lines:
                line_rows.append(
                    [
                        estimate.scenario.name,
                        line.line_id,
                        line.quantity_id,
                        line.source_object_id,
                        line.source_level_id or "",
                        line.work_section,
                        line.material or "",
                        line.quantity_type,
                        line.cost_code,
                        line.description,
                        line.base_quantity,
                        line.waste_percent,
                        line.priced_quantity,
                        line.unit,
                        line.base_unit_rate,
                        line.adjusted_unit_rate,
                        line.material_cost,
                        line.labor_cost,
                        line.equipment_cost,
                        line.subcontract_cost,
                        line.other_cost,
                        line.direct_cost,
                        line.currency,
                        "; ".join(line.drawing_refs),
                    ]
                )

        issue_rows: list[list[Any]] = [
            ["Code", "Severity", "Scenario", "Quantity", "Object", "Rate", "Message"]
        ]
        for issue in report.issues:
            issue_rows.append(
                [
                    issue.code,
                    issue.severity,
                    issue.scenario_id or "",
                    issue.quantity_id or "",
                    issue.source_object_id or "",
                    issue.rate_item_id or "",
                    issue.message,
                ]
            )

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_relationships_xml())
            archive.writestr("docProps/core.xml", self._core_properties_xml())
            archive.writestr("docProps/app.xml", self._app_properties_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_relationships_xml())
            archive.writestr("xl/worksheets/sheet1.xml", self._worksheet_xml(summary_rows))
            archive.writestr("xl/worksheets/sheet2.xml", self._worksheet_xml(line_rows))
            archive.writestr("xl/worksheets/sheet3.xml", self._worksheet_xml(issue_rows))
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
                    cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>')
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
            '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
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
            '<sheet name="Summary" sheetId="1" r:id="rId1"/>'
            '<sheet name="Cost Lines" sheetId="2" r:id="rId2"/>'
            '<sheet name="Issues" sheetId="3" r:id="rId3"/>'
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
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
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
            '<dc:title>BB21 Cost Estimate</dc:title>'
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
