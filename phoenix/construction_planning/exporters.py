"""Dependency-free BB24 JSON, CSV, XLSX, HTML, SVG and dossier exports."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import PlanningReport, ScenarioResult


_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class ConstructionPlanningExporter:
    def export_all(
        self,
        report: PlanningReport,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {
            "json": self.export_json(
                report,
                root / "construction_schedule.json",
            ),
            "schedule_csv": self.export_schedule_csv(
                report,
                root / "construction_schedule.csv",
            ),
            "cashflow_csv": self.export_cashflow_csv(
                report,
                root / "construction_cashflow.csv",
            ),
            "resources_csv": self.export_resources_csv(
                report,
                root / "construction_resources.csv",
            ),
            "xlsx": self.export_xlsx(
                report,
                root / "construction_schedule.xlsx",
            ),
            "html": self.export_html(
                report,
                root / "construction_schedule_gantt.html",
            ),
            "svg": self.export_svg(
                report,
                root / "construction_schedule_gantt.svg",
            ),
        }
        paths["checksums"] = self.export_checksums(
            paths,
            root / "checksums.sha256",
        )
        paths["dossier"] = self.export_dossier_zip(
            report,
            paths,
            root / "construction_planning_dossier.zip",
        )
        return paths

    def export_json(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.write_text(
            json.dumps(
                report.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def export_schedule_csv(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        fields = [
            "scenario_id",
            "activity_id",
            "wbs_code",
            "name",
            "discipline",
            "predecessor_ids",
            "duration_workdays",
            "start_date",
            "finish_date",
            "total_float_workdays",
            "critical",
            "milestone",
            "direct_cost",
            "source_object_ids",
            "quantity_ids",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for scenario in report.scenarios:
                for activity in scenario.activities:
                    data = activity.to_dict()
                    writer.writerow(
                        {
                            "scenario_id": scenario.scenario_id,
                            **{
                                field: (
                                    "; ".join(data[field])
                                    if isinstance(data.get(field), list)
                                    else data.get(field)
                                )
                                for field in fields
                                if field != "scenario_id"
                            },
                        }
                    )
        return path

    def export_cashflow_csv(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "scenario_id",
                    "month",
                    "currency",
                    "period_cost",
                    "cumulative_cost",
                ],
            )
            writer.writeheader()
            for scenario in report.scenarios:
                for item in scenario.cashflow_by_month:
                    writer.writerow(
                        {
                            "scenario_id": scenario.scenario_id,
                            "month": item["month"],
                            "currency": report.currency,
                            "period_cost": item["period_cost"],
                            "cumulative_cost": item["cumulative_cost"],
                        }
                    )
        return path

    def export_resources_csv(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "scenario_id",
                    "resource",
                    "total_resource_days",
                    "peak_concurrent",
                ],
            )
            writer.writeheader()
            for scenario in report.scenarios:
                for resource, summary in scenario.resource_summary.items():
                    writer.writerow(
                        {
                            "scenario_id": scenario.scenario_id,
                            "resource": resource,
                            **summary,
                        }
                    )
        return path

    def export_xlsx(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        baseline = report.baseline

        summary_rows: list[list[Any]] = [
            ["PROJECT-PHOENIX BB24 Construction Planning"],
            ["Project ID", report.project_id],
            ["Project name", report.project_name],
            ["Project start", report.project_start_date],
            ["Currency", report.currency],
            ["Planning passed", report.planning_passed],
            [],
            ["Scenario comparison"],
            [
                "Scenario",
                "Duration workdays",
                "Finish date",
                "Direct cost",
                "Critical activities",
            ],
        ]
        for scenario in report.scenarios:
            summary_rows.append(
                [
                    scenario.name,
                    scenario.project_duration_workdays,
                    scenario.project_finish_date,
                    scenario.total_direct_cost,
                    len(scenario.critical_path),
                ]
            )

        schedule_rows: list[list[Any]] = [
            [
                "Activity ID",
                "WBS",
                "Activity",
                "Discipline",
                "Predecessors",
                "Duration",
                "Start",
                "Finish",
                "Float",
                "Critical",
                "Milestone",
                "Direct cost",
            ]
        ]
        for item in baseline.activities:
            schedule_rows.append(
                [
                    item.activity_id,
                    item.wbs_code,
                    item.name,
                    item.discipline,
                    "; ".join(item.predecessor_ids),
                    item.duration_workdays,
                    item.start_date,
                    item.finish_date,
                    item.total_float_workdays,
                    item.critical,
                    item.milestone,
                    item.direct_cost,
                ]
            )

        resource_rows: list[list[Any]] = [
            [
                "Resource",
                "Total resource-days",
                "Peak concurrent",
            ]
        ]
        for resource, item in baseline.resource_summary.items():
            resource_rows.append(
                [
                    resource,
                    item["total_resource_days"],
                    item["peak_concurrent"],
                ]
            )

        cashflow_rows: list[list[Any]] = [
            ["Month", "Period cost", "Cumulative cost"]
        ]
        for item in baseline.cashflow_by_month:
            cashflow_rows.append(
                [
                    item["month"],
                    item["period_cost"],
                    item["cumulative_cost"],
                ]
            )

        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            self._zip_write(
                archive,
                "[Content_Types].xml",
                self._content_types_xml(),
            )
            self._zip_write(
                archive,
                "_rels/.rels",
                self._root_relationships_xml(),
            )
            self._zip_write(
                archive,
                "docProps/core.xml",
                self._core_properties_xml(report),
            )
            self._zip_write(
                archive,
                "docProps/app.xml",
                self._app_properties_xml(),
            )
            self._zip_write(
                archive,
                "xl/workbook.xml",
                self._workbook_xml(),
            )
            self._zip_write(
                archive,
                "xl/_rels/workbook.xml.rels",
                self._workbook_relationships_xml(),
            )
            self._zip_write(
                archive,
                "xl/styles.xml",
                self._styles_xml(),
            )
            self._zip_write(
                archive,
                "xl/worksheets/sheet1.xml",
                self._worksheet_xml(summary_rows, header_rows={1, 8, 9}),
            )
            self._zip_write(
                archive,
                "xl/worksheets/sheet2.xml",
                self._worksheet_xml(schedule_rows, header_rows={1}),
            )
            self._zip_write(
                archive,
                "xl/worksheets/sheet3.xml",
                self._worksheet_xml(resource_rows, header_rows={1}),
            )
            self._zip_write(
                archive,
                "xl/worksheets/sheet4.xml",
                self._worksheet_xml(cashflow_rows, header_rows={1}),
            )
        return path

    def export_html(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        baseline = report.baseline
        duration = max(baseline.project_duration_workdays, 1)
        rows: list[str] = []
        for activity in baseline.activities:
            left = activity.early_start_day / duration * 100
            width = max(
                activity.duration_workdays / duration * 100,
                0.8 if activity.milestone else 1.2,
            )
            css_class = "critical" if activity.critical else "normal"
            marker = "milestone" if activity.milestone else css_class
            rows.append(
                "<tr>"
                f"<td>{html.escape(activity.wbs_code)}</td>"
                f"<td>{html.escape(activity.name)}</td>"
                f"<td>{activity.start_date}</td>"
                f"<td>{activity.finish_date}</td>"
                f"<td>{activity.duration_workdays}</td>"
                "<td class=\"timeline\">"
                f"<div class=\"bar {marker}\" style=\"left:{left:.3f}%;"
                f"width:{width:.3f}%\"></div>"
                "</td></tr>"
            )

        scenario_cards = "".join(
            "<div class=\"card\">"
            f"<strong>{html.escape(item.name)}</strong><br>"
            f"{item.project_duration_workdays} workdays<br>"
            f"Finish: {item.project_finish_date}<br>"
            f"{html.escape(report.currency)} {item.total_direct_cost:,.2f}"
            "</div>"
            for item in report.scenarios
        )

        path.write_text(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(report.project_name)} schedule</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;margin:32px;color:#222}"
            "h1{margin-bottom:4px}.meta{color:#555;margin-bottom:18px}"
            ".cards{display:flex;gap:12px;margin:18px 0}.card{border:1px solid #bbb;"
            "padding:12px;min-width:170px;border-radius:6px;background:#f7f7f7}"
            "table{border-collapse:collapse;width:100%;font-size:13px}"
            "th,td{border:1px solid #ccc;padding:6px;text-align:left}"
            "th{background:#263238;color:white}.timeline{position:relative;"
            "height:22px;min-width:420px;background:repeating-linear-gradient("
            "90deg,#fafafa,#fafafa 9.8%,#e8e8e8 10%)}"
            ".bar{position:absolute;top:4px;height:14px;border-radius:3px}"
            ".bar.normal{background:#607d8b}.bar.critical{background:#c62828}"
            ".bar.milestone{background:#6a1b9a;transform:rotate(45deg);"
            "width:12px!important;height:12px;top:5px}"
            "</style></head><body>"
            f"<h1>{html.escape(report.project_name)}</h1>"
            f"<div class=\"meta\">Project {html.escape(report.project_id)} | "
            f"Start {report.project_start_date} | Currency "
            f"{html.escape(report.currency)}</div>"
            f"<div class=\"cards\">{scenario_cards}</div>"
            "<h2>Baseline Gantt</h2><table><thead><tr>"
            "<th>WBS</th><th>Activity</th><th>Start</th><th>Finish</th>"
            "<th>Days</th><th>Timeline</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></body></html>",
            encoding="utf-8",
        )
        return path

    def export_svg(
        self,
        report: PlanningReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        baseline = report.baseline
        row_height = 28
        label_width = 360
        timeline_width = 900
        width = label_width + timeline_width + 40
        height = 100 + row_height * len(baseline.activities)
        duration = max(baseline.project_duration_workdays, 1)

        content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            '<rect width="100%" height="100%" fill="white"/>',
            (
                f'<text x="20" y="30" font-family="Arial" font-size="20" '
                f'font-weight="bold">{escape(report.project_name)}</text>'
            ),
            (
                f'<text x="20" y="52" font-family="Arial" font-size="12">'
                f'Baseline: {baseline.project_duration_workdays} workdays, '
                f'finish {baseline.project_finish_date}</text>'
            ),
        ]
        for index, activity in enumerate(baseline.activities):
            y = 78 + index * row_height
            x = label_width + (
                activity.early_start_day / duration * timeline_width
            )
            bar_width = max(
                activity.duration_workdays / duration * timeline_width,
                8,
            )
            fill = "#c62828" if activity.critical else "#607d8b"
            content.append(
                f'<text x="20" y="{y + 14}" font-family="Arial" font-size="11">'
                f'{escape(activity.wbs_code)} {escape(activity.name)}</text>'
            )
            content.append(
                f'<line x1="{label_width}" y1="{y + 20}" '
                f'x2="{label_width + timeline_width}" y2="{y + 20}" '
                'stroke="#eeeeee"/>'
            )
            if activity.milestone:
                center = x + 6
                content.append(
                    f'<polygon points="{center},{y + 5} {center + 7},{y + 12} '
                    f'{center},{y + 19} {center - 7},{y + 12}" fill="#6a1b9a"/>'
                )
            else:
                content.append(
                    f'<rect x="{x:.2f}" y="{y + 5}" width="{bar_width:.2f}" '
                    f'height="14" rx="3" fill="{fill}"/>'
                )
        content.append("</svg>")
        path.write_text("\n".join(content), encoding="utf-8")
        return path

    def export_checksums(
        self,
        paths: dict[str, Path],
        output_path: str | Path,
    ) -> Path:
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
        report: PlanningReport,
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
                    "PROJECT-PHOENIX BB24 CONSTRUCTION PLANNING DOSSIER\n"
                    f"Project: {report.project_name} ({report.project_id})\n"
                    f"Start date: {report.project_start_date}\n"
                    f"Baseline finish: {report.baseline.project_finish_date}\n"
                    f"Currency: {report.currency}\n"
                    "This schedule is non-certifying until reviewed and approved.\n"
                ),
            )
        return path

    @staticmethod
    def _zip_write(
        archive: zipfile.ZipFile,
        name: str,
        text: str,
    ) -> None:
        ConstructionPlanningExporter._zip_write_bytes(
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
    def _cell_reference(column_index: int, row_index: int) -> str:
        letters = ""
        value = column_index
        while value:
            value, remainder = divmod(value - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row_index}"

    def _worksheet_xml(
        self,
        rows: list[list[Any]],
        *,
        header_rows: set[int],
    ) -> str:
        xml_rows: list[str] = []
        max_columns = max((len(row) for row in rows), default=1)
        for row_index, row in enumerate(rows, start=1):
            cells: list[str] = []
            style = 1 if row_index in header_rows else 0
            for column_index, value in enumerate(row, start=1):
                ref = self._cell_reference(column_index, row_index)
                if isinstance(value, bool):
                    cells.append(
                        f'<c r="{ref}" s="{style}" t="b"><v>{int(value)}</v></c>'
                    )
                elif isinstance(value, (int, float)):
                    cells.append(
                        f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
                    )
                else:
                    text = escape("" if value is None else str(value))
                    cells.append(
                        f'<c r="{ref}" s="{style}" t="inlineStr">'
                        f'<is><t>{text}</t></is></c>'
                    )
            xml_rows.append(
                f'<row r="{row_index}">{"".join(cells)}</row>'
            )

        columns = "".join(
            f'<col min="{index}" max="{index}" width="'
            + (
                "34" if index in {2, 3} else
                "18" if index in {4, 5, 7, 8} else
                "14"
            )
            + '" customWidth="1"/>'
            for index in range(1, max_columns + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<cols>{columns}</cols>'
            '<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            '</worksheet>'
        )

    @staticmethod
    def _content_types_xml() -> str:
        sheets = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, 5)
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
        names = ["Summary", "Schedule", "Resources", "Cashflow"]
        sheets = "".join(
            f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
            for index, name in enumerate(names, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{sheets}</sheets></workbook>'
        )

    @staticmethod
    def _workbook_relationships_xml() -> str:
        relationships = "".join(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, 5)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{relationships}'
            '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _styles_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="10"/><name val="Arial"/></font>'
            '<font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font></fonts>'
            '<fills count="3"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FF263238"/>'
            '<bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>'
        )

    @staticmethod
    def _core_properties_xml(report: PlanningReport) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            f'<dc:title>{escape(report.project_name)} construction schedule</dc:title>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-01T00:00:00Z</dcterms:created>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _app_properties_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>PROJECT-PHOENIX</Application></Properties>'
        )
