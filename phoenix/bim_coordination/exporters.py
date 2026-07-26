"""JSON, CSV, XLSX and BCF-foundation exports for BB22."""

from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .models import CoordinationReport


class BimCoordinationExporter:
    def export_json(
        self,
        report: CoordinationReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
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

    def export_csv(
        self,
        report: CoordinationReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "issue_id",
            "issue_type",
            "title",
            "description",
            "severity",
            "status",
            "discipline",
            "source_model",
            "source_object_id",
            "target_model",
            "target_object_id",
            "level_id",
            "location",
            "evidence",
            "assigned_to",
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for issue in report.issues:
                data = issue.to_dict()
                writer.writerow(
                    {
                        field: (
                            json.dumps(
                                data[field],
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            if isinstance(data.get(field), (dict, list))
                            else data.get(field)
                        )
                        for field in fields
                    }
                )
        return path

    def export_xlsx(
        self,
        report: CoordinationReport,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        issue_rows: list[list[Any]] = [
            [
                "Issue ID",
                "Type",
                "Severity",
                "Status",
                "Title",
                "Discipline",
                "Source Model",
                "Source Object",
                "Target Model",
                "Target Object",
                "Level",
                "Location",
                "Description",
            ]
        ]
        for issue in report.issues:
            data = issue.to_dict()
            issue_rows.append(
                [
                    data["issue_id"],
                    data["issue_type"],
                    data["severity"],
                    data["status"],
                    data["title"],
                    data["discipline"],
                    data["source_model"] or "",
                    data["source_object_id"] or "",
                    data["target_model"] or "",
                    data["target_object_id"] or "",
                    data["level_id"] or "",
                    json.dumps(data["location"], sort_keys=True),
                    data["description"],
                ]
            )

        summary_rows: list[list[Any]] = [
            ["PROJECT-PHOENIX BB22 BIM Coordination"],
            ["Project ID", report.project_id],
            ["Engine version", report.engine_version],
            ["Coordination passed", report.coordination_passed],
            ["Issue count", len(report.issues)],
            ["Open issue count", report.open_issue_count],
            [],
            ["Summary by severity"],
            ["Severity", "Count"],
        ]
        for key, value in report.summary_by_severity.items():
            summary_rows.append([key, value])

        summary_rows.extend([[], ["Summary by type"], ["Issue Type", "Count"]])
        for key, value in report.summary_by_type.items():
            summary_rows.append([key, value])

        summary_rows.extend(
            [
                [],
                ["Model fingerprints"],
                ["Model", "SHA-256"],
            ]
        )
        for key, value in sorted(report.model_fingerprints_sha256.items()):
            summary_rows.append([key, value])

        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "[Content_Types].xml",
                self._content_types_xml(),
            )
            archive.writestr(
                "_rels/.rels",
                self._root_relationships_xml(),
            )
            archive.writestr(
                "docProps/core.xml",
                self._core_properties_xml(),
            )
            archive.writestr(
                "docProps/app.xml",
                self._app_properties_xml(),
            )
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                self._workbook_relationships_xml(),
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                self._worksheet_xml(issue_rows),
            )
            archive.writestr(
                "xl/worksheets/sheet2.xml",
                self._worksheet_xml(summary_rows),
            )
        return path

    def export_bcfzip(
        self,
        report: CoordinationReport,
        output_path: str | Path,
    ) -> Path:
        """Create a BCF-compatible foundation package.

        It contains BCF version/project metadata and one topic folder per issue.
        Viewpoints contain the issue location and source/target component IDs.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "bcf.version",
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Version VersionId="3.0" '
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>'
                ),
            )
            archive.writestr(
                "project.bcfp",
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<ProjectExtension>'
                    f'<Project ProjectId="{escape(report.project_id)}">'
                    f'<Name>{escape(report.project_id)}</Name>'
                    '</Project>'
                    '</ProjectExtension>'
                ),
            )

            for issue in report.issues:
                folder = issue.issue_id
                archive.writestr(
                    f"{folder}/markup.bcf",
                    self._bcf_markup(issue),
                )
                archive.writestr(
                    f"{folder}/viewpoint.bcfv",
                    self._bcf_viewpoint(issue),
                )
        return path

    @staticmethod
    def _bcf_markup(issue: Any) -> str:
        assigned = (
            f"<AssignedTo>{escape(issue.assigned_to)}</AssignedTo>"
            if issue.assigned_to
            else ""
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Markup>'
            '<Topic>'
            f'<Guid>{escape(issue.issue_id)}</Guid>'
            f'<TopicType>{escape(issue.issue_type)}</TopicType>'
            f'<TopicStatus>{escape(issue.status.value)}</TopicStatus>'
            f'<Title>{escape(issue.title)}</Title>'
            f'<Priority>{escape(issue.severity.value)}</Priority>'
            f'<Description>{escape(issue.description)}</Description>'
            f'{assigned}'
            '</Topic>'
            '<Viewpoints>'
            '<ViewPoint Guid="VIEWPOINT-1">'
            '<Viewpoint>viewpoint.bcfv</Viewpoint>'
            '</ViewPoint>'
            '</Viewpoints>'
            '</Markup>'
        )

    @staticmethod
    def _bcf_viewpoint(issue: Any) -> str:
        location = issue.location or {}
        x = float(location.get("x_m", 0.0))
        y = float(location.get("y_m", 0.0))
        z = float(location.get("z_m", 0.0))

        components: list[str] = []
        for object_id in (
            issue.source_object_id,
            issue.target_object_id,
        ):
            if object_id:
                components.append(
                    f'<Component IfcGuid="{escape(object_id)}" Selected="true"/>'
                )

        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<VisualizationInfo Guid="VIEWPOINT-1">'
            f'<Components>{"".join(components)}</Components>'
            '<PerspectiveCamera>'
            f'<CameraViewPoint><X>{x}</X><Y>{y}</Y><Z>{z + 10.0}</Z></CameraViewPoint>'
            '<CameraDirection><X>0</X><Y>0</Y><Z>-1</Z></CameraDirection>'
            '<CameraUpVector><X>0</X><Y>1</Y><Z>0</Z></CameraUpVector>'
            '<FieldOfView>60</FieldOfView>'
            '</PerspectiveCamera>'
            '</VisualizationInfo>'
        )

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
                reference = self._cell_reference(
                    column_index,
                    row_index,
                )
                if isinstance(value, bool):
                    cells.append(
                        f'<c r="{reference}" t="b"><v>{int(value)}</v></c>'
                    )
                elif isinstance(value, (int, float)):
                    cells.append(
                        f'<c r="{reference}"><v>{value}</v></c>'
                    )
                else:
                    text = escape("" if value is None else str(value))
                    cells.append(
                        f'<c r="{reference}" t="inlineStr">'
                        f'<is><t>{text}</t></is></c>'
                    )
            xml_rows.append(
                f'<row r="{row_index}">{"".join(cells)}</row>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            '</worksheet>'
        )

    @staticmethod
    def _content_types_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types '
            'xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _root_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _workbook_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook '
            'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            '<sheet name="Issues" sheetId="1" r:id="rId1"/>'
            '<sheet name="Summary" sheetId="2" r:id="rId2"/>'
            '</sheets>'
            '</workbook>'
        )

    @staticmethod
    def _workbook_relationships_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet2.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _core_properties_xml() -> str:
        timestamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>PROJECT-PHOENIX</dc:creator>'
            '<dc:title>BB22 BIM Coordination</dc:title>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
            '</cp:coreProperties>'
        )

    @staticmethod
    def _app_properties_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties '
            'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>PROJECT-PHOENIX</Application>'
            '</Properties>'
        )
