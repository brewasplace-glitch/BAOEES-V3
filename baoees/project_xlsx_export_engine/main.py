import html
import zipfile
from datetime import datetime
from pathlib import Path


class ProjectXlsxExportEngine:

    def __init__(self):
        self.xlsx_result = {}

    def export_project_xlsx(
        self,
        project_result=None,
        storage_result=None,
        cost_result=None,
        planning_result=None,
        quantity_result=None,
        validation_result=None,
        runtime_result=None,
        csv_excel_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        quantity_result = quantity_result or {}
        validation_result = validation_result or {}
        runtime_result = runtime_result or {}
        csv_excel_result = csv_excel_result or {}

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        exports_dir = Path(
            folder_structure.get(
                "exports",
                project_output_dir / "09_exports"
            )
        )

        exports_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        xlsx_path = exports_dir / f"{project_id}_project_tables.xlsx"

        worksheets = {
            "Project": self.build_project_rows(
                project_result=project_result,
                storage_result=storage_result,
                runtime_result=runtime_result
            ),
            "Kosten": self.build_cost_rows(cost_result=cost_result),
            "Planning": self.build_planning_rows(planning_result=planning_result),
            "Hoeveelheden": self.build_quantity_rows(quantity_result=quantity_result),
            "QA_QC": self.build_validation_rows(validation_result=validation_result),
            "Index": self.build_index_rows(
                cost_result=cost_result,
                planning_result=planning_result,
                quantity_result=quantity_result,
                validation_result=validation_result,
                csv_excel_result=csv_excel_result
            )
        }

        xlsx_file_result = self.write_xlsx_file(
            xlsx_path=xlsx_path,
            worksheets=worksheets
        )

        self.xlsx_result = {
            "engine": "ProjectXlsxExportEngine",
            "version": "1.0",
            "status": "PROJECT_XLSX_FILE_OPGESLAGEN",
            "calculation_level": "basis XLSX Excel-export met meerdere werkbladen",
            "project_id": project_id,
            "project_name": project_name,
            "exports_dir": str(exports_dir),
            "xlsx_file": xlsx_file_result,
            "worksheet_count": len(worksheets),
            "worksheets": list(worksheets.keys()),
            "cost_engine_status": cost_result.get("status", "ONBEKEND"),
            "planning_engine_status": planning_result.get("status", "ONBEKEND"),
            "quantity_engine_status": quantity_result.get("status", "ONBEKEND"),
            "validation_engine_status": validation_result.get("status", "ONBEKEND"),
            "runtime_engine_status": runtime_result.get("status", "ONBEKEND"),
            "csv_excel_engine_status": csv_excel_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(xlsx_file_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project XLSX Export Engine v1.0 maakt een echte basis-XLSX als Office Open XML zip-bestand. "
                "De volgende versie kan worden uitgebreid met professionele opmaak, filters, kolombreedtes, "
                "formules, grafieken en dashboards."
            )
        }

        return self.xlsx_result

    def write_xlsx_file(self, xlsx_path, worksheets):
        xlsx_path = Path(xlsx_path)
        xlsx_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(xlsx_path, "w", zipfile.ZIP_DEFLATED) as xlsx:
                xlsx.writestr("[Content_Types].xml", self.content_types_xml(len(worksheets)))
                xlsx.writestr("_rels/.rels", self.root_rels_xml())
                xlsx.writestr("xl/workbook.xml", self.workbook_xml(worksheets))
                xlsx.writestr("xl/_rels/workbook.xml.rels", self.workbook_rels_xml(worksheets))
                xlsx.writestr("xl/styles.xml", self.styles_xml())

                for index, rows in enumerate(worksheets.values(), start=1):
                    xlsx.writestr(
                        f"xl/worksheets/sheet{index}.xml",
                        self.worksheet_xml(rows)
                    )

            return {
                "path": str(xlsx_path),
                "status": "OPGESLAGEN",
                "exists": xlsx_path.exists(),
                "size_bytes": xlsx_path.stat().st_size if xlsx_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(xlsx_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_project_rows(
        self,
        project_result,
        storage_result,
        runtime_result
    ):
        return [
            ["Onderdeel", "Waarde"],
            ["Project-ID", storage_result.get("project_id", "unknown_project")],
            ["Projectnaam", project_result.get("project_name", "Onbekend project")],
            ["Projecttype", project_result.get("project_type", "Onbekend")],
            ["Locatie", project_result.get("location", "Onbekend")],
            ["Land", project_result.get("country", "Onbekend")],
            ["Runtime mode", project_result.get("runtime_mode", "onbekend")],
            ["Project outputmap", storage_result.get("project_output_dir", "ONBEKEND")],
            ["Runtime status", runtime_result.get("status", "ONBEKEND")],
            ["Exportdatum", datetime.now().isoformat(timespec="seconds")]
        ]

    def build_cost_rows(self, cost_result):
        rows = [
            ["Kostenpost", "Omschrijving", "Bedrag", "Eenheid", "Status"]
        ]

        cost_items = (
            cost_result.get("cost_items")
            or cost_result.get("items")
            or cost_result.get("estimate_items")
            or []
        )

        if isinstance(cost_items, list) and cost_items:
            for item in cost_items:
                if isinstance(item, dict):
                    rows.append([
                        item.get("name", item.get("cost_item", "Onbekende kostenpost")),
                        item.get("description", ""),
                        item.get("amount", item.get("cost", item.get("value", ""))),
                        item.get("unit", "EUR"),
                        item.get("status", cost_result.get("status", "CONCEPT"))
                    ])

        if len(rows) == 1:
            rows.extend([
                ["Voorbereiding", "Conceptuele projectvoorbereiding", "0", "EUR", "CONCEPT"],
                ["Ontwerp", "Conceptueel ontwerp en engineering", "0", "EUR", "CONCEPT"],
                ["Vergunningen", "Vergunningvoorbereiding", "0", "EUR", "CONCEPT"],
                ["Uitvoering", "Uitvoeringskosten nader te bepalen", "0", "EUR", "CONCEPT"],
                ["Onvoorzien", "Risicoreservering nader te bepalen", "0", "EUR", "CONCEPT"]
            ])

        rows.append([])
        rows.append(["Engine status", cost_result.get("status", "ONBEKEND")])
        rows.append(["Advies", str(cost_result.get("recommendation", "Niet beschikbaar"))])

        return rows

    def build_planning_rows(self, planning_result):
        rows = [
            ["Fase", "Omschrijving", "Start", "Einde", "Duur", "Status"]
        ]

        planning_items = (
            planning_result.get("planning_items")
            or planning_result.get("phases")
            or planning_result.get("schedule")
            or []
        )

        if isinstance(planning_items, list) and planning_items:
            for item in planning_items:
                if isinstance(item, dict):
                    rows.append([
                        item.get("phase", item.get("name", "Onbekende fase")),
                        item.get("description", ""),
                        item.get("start", item.get("start_date", "")),
                        item.get("end", item.get("end_date", "")),
                        item.get("duration", ""),
                        item.get("status", planning_result.get("status", "CONCEPT"))
                    ])

        if len(rows) == 1:
            rows.extend([
                ["1", "Projectanalyse", "", "", "nader te bepalen", "CONCEPT"],
                ["2", "Variantenstudie", "", "", "nader te bepalen", "CONCEPT"],
                ["3", "Voorontwerp", "", "", "nader te bepalen", "CONCEPT"],
                ["4", "Vergunningen", "", "", "nader te bepalen", "CONCEPT"],
                ["5", "Technische uitwerking", "", "", "nader te bepalen", "CONCEPT"],
                ["6", "Aanbesteding", "", "", "nader te bepalen", "CONCEPT"],
                ["7", "Uitvoering", "", "", "nader te bepalen", "CONCEPT"],
                ["8", "Oplevering", "", "", "nader te bepalen", "CONCEPT"]
            ])

        rows.append([])
        rows.append(["Engine status", planning_result.get("status", "ONBEKEND")])
        rows.append(["Advies", str(planning_result.get("recommendation", "Niet beschikbaar"))])

        return rows

    def build_quantity_rows(self, quantity_result):
        rows = [
            ["Post", "Omschrijving", "Hoeveelheid", "Eenheid", "Status"]
        ]

        quantity_items = (
            quantity_result.get("quantity_items")
            or quantity_result.get("boq_items")
            or quantity_result.get("items")
            or []
        )

        if isinstance(quantity_items, list) and quantity_items:
            for item in quantity_items:
                if isinstance(item, dict):
                    rows.append([
                        item.get("item", item.get("name", "Onbekende post")),
                        item.get("description", ""),
                        item.get("quantity", item.get("amount", "")),
                        item.get("unit", ""),
                        item.get("status", quantity_result.get("status", "CONCEPT"))
                    ])

        if len(rows) == 1:
            rows.extend([
                ["01", "Grondwerk", "0", "m3", "CONCEPT"],
                ["02", "Fundering", "0", "m1/m3", "CONCEPT"],
                ["03", "Constructie", "0", "kg/m3/m2", "CONCEPT"],
                ["04", "Gevels", "0", "m2", "CONCEPT"],
                ["05", "Dak", "0", "m2", "CONCEPT"],
                ["06", "Riolering en afwatering", "0", "m1/st", "CONCEPT"],
                ["07", "Terrein en verharding", "0", "m2", "CONCEPT"]
            ])

        rows.append([])
        rows.append(["Engine status", quantity_result.get("status", "ONBEKEND")])
        rows.append(["Advies", str(quantity_result.get("recommendation", "Niet beschikbaar"))])

        return rows

    def build_validation_rows(self, validation_result):
        rows = [
            ["Controlepunt", "Resultaat", "Status", "Opmerking"]
        ]

        checks = (
            validation_result.get("checks")
            or validation_result.get("qa_qc_checks")
            or validation_result.get("validation_checks")
            or []
        )

        if isinstance(checks, list) and checks:
            for check in checks:
                if isinstance(check, dict):
                    rows.append([
                        check.get("name", check.get("check", "Onbekende controle")),
                        check.get("result", ""),
                        check.get("status", validation_result.get("status", "CONCEPT")),
                        check.get("remark", check.get("note", ""))
                    ])

        if len(rows) == 1:
            rows.extend([
                ["Projectinvoer aanwezig", "Te controleren", "CONCEPT", ""],
                ["Digital Twin gevuld", "Te controleren", "CONCEPT", ""],
                ["Bronregister aanwezig", "Te controleren", "CONCEPT", ""],
                ["Rapporten gegenereerd", "Te controleren", "CONCEPT", ""],
                ["Tekeningen gegenereerd", "Te controleren", "CONCEPT", ""],
                ["ZIP-export aanwezig", "Te controleren", "CONCEPT", ""]
            ])

        rows.append([])
        rows.append(["Engine status", validation_result.get("status", "ONBEKEND")])
        rows.append(["Go/No-Go advies", str(validation_result.get("go_no_go_advice", "Niet beschikbaar"))])

        return rows

    def build_index_rows(
        self,
        cost_result,
        planning_result,
        quantity_result,
        validation_result,
        csv_excel_result
    ):
        return [
            ["Werkblad", "Bron-engine", "Status", "Opmerking"],
            ["Project", "Project Analyzer / Storage Engine", "GEREED", "Projectbasisgegevens"],
            ["Kosten", "Cost Estimate Engine", cost_result.get("status", "ONBEKEND"), "Kostenraming"],
            ["Planning", "Planning Engine", planning_result.get("status", "ONBEKEND"), "Projectplanning"],
            ["Hoeveelheden", "Quantity / BOQ Engine", quantity_result.get("status", "ONBEKEND"), "Hoeveelhedenstaat"],
            ["QA_QC", "Validation & QA/QC Engine", validation_result.get("status", "ONBEKEND"), "Controleoverzicht"],
            ["CSV Export", "Project CSV/Excel Export Engine", csv_excel_result.get("status", "ONBEKEND"), "Parallelle CSV-tabellen"],
            ["Exportdatum", "Project XLSX Export Engine", datetime.now().isoformat(timespec="seconds"), ""]
        ]

    def content_types_xml(self, sheet_count):
        overrides = []

        overrides.append(
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        )

        overrides.append(
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        )

        for index in range(1, sheet_count + 1):
            overrides.append(
                f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {"".join(overrides)}
</Types>'''

    def root_rels_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="xl/workbook.xml"/>
</Relationships>'''

    def workbook_xml(self, worksheets):
        sheet_lines = []

        for index, sheet_name in enumerate(worksheets.keys(), start=1):
            safe_name = self.safe_sheet_name(sheet_name)
            sheet_lines.append(
                f'<sheet name="{safe_name}" sheetId="{index}" r:id="rId{index}"/>'
            )

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    {"".join(sheet_lines)}
  </sheets>
</workbook>'''

    def workbook_rels_xml(self, worksheets):
        rel_lines = []

        for index in range(1, len(worksheets) + 1):
            rel_lines.append(
                f'<Relationship Id="rId{index}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{index}.xml"/>'
            )

        style_id = len(worksheets) + 1

        rel_lines.append(
            f'<Relationship Id="rId{style_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
        )

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(rel_lines)}
</Relationships>'''

    def styles_xml(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1">
    <font>
      <sz val="11"/>
      <name val="Calibri"/>
    </font>
  </fonts>
  <fills count="1">
    <fill>
      <patternFill patternType="none"/>
    </fill>
  </fills>
  <borders count="1">
    <border/>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  </cellXfs>
</styleSheet>'''

    def worksheet_xml(self, rows):
        row_lines = []

        for row_index, row in enumerate(rows, start=1):
            cell_lines = []

            for col_index, value in enumerate(row, start=1):
                cell_ref = f"{self.column_letter(col_index)}{row_index}"
                cell_lines.append(self.cell_xml(cell_ref, value))

            row_lines.append(
                f'<row r="{row_index}">{"".join(cell_lines)}</row>'
            )

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(row_lines)}
  </sheetData>
</worksheet>'''

    def cell_xml(self, cell_ref, value):
        if value is None:
            value = ""

        value_text = str(value)

        if self.is_number(value_text):
            return f'<c r="{cell_ref}"><v>{value_text}</v></c>'

        safe_value = html.escape(value_text)

        return f'<c r="{cell_ref}" t="inlineStr"><is><t>{safe_value}</t></is></c>'

    def is_number(self, value):
        try:
            if value.strip() == "":
                return False
            float(value)
            return True
        except Exception:
            return False

    def column_letter(self, index):
        letters = ""

        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters

        return letters

    def safe_sheet_name(self, sheet_name):
        unsafe = ["\\", "/", "*", "[", "]", ":", "?"]
        safe = str(sheet_name)

        for character in unsafe:
            safe = safe.replace(character, "_")

        return html.escape(safe[:31])

    def build_warnings(self, xlsx_file_result):
        warnings = []

        if xlsx_file_result.get("status") != "OPGESLAGEN":
            warnings.append("XLSX-bestand is niet opgeslagen.")

        if not warnings:
            warnings.append("Geen kritieke XLSX-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_XLSX_EXPORT_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste echte Excel XLSX-exportlaag. "
                "De volgende stap is uitbreiding met opmaak, filters, formules, grafieken "
                "en projectdashboards."
            ),
            "next_steps": [
                "ProjectXlsxExportEngine koppelen aan BAOEES Core",
                "XLSX-bestand opnemen in ZIP-export",
                "kolombreedtes toevoegen",
                "koprijen vet maken",
                "filters toevoegen",
                "kostenformules toevoegen",
                "dashboardtabblad toevoegen",
                "grafieken toevoegen"
            ]
        }

    def get_xlsx_result(self):
        return self.xlsx_result

    def run(self):
        print("Project XLSX Export Engine actief")