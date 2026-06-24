import csv
from datetime import datetime
from pathlib import Path


class ProjectCsvExcelExportEngine:

    def __init__(self):
        self.csv_excel_result = {}

    def export_project_tables(
        self,
        project_result=None,
        storage_result=None,
        cost_result=None,
        planning_result=None,
        quantity_result=None,
        validation_result=None,
        runtime_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        cost_result = cost_result or {}
        planning_result = planning_result or {}
        quantity_result = quantity_result or {}
        validation_result = validation_result or {}
        runtime_result = runtime_result or {}

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

        calculations_dir = Path(
            folder_structure.get(
                "calculations",
                project_output_dir / "04_calculations"
            )
        )

        exports_dir.mkdir(parents=True, exist_ok=True)
        calculations_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        written_files = []

        written_files.append(
            self.write_csv(
                file_path=exports_dir / f"{project_id}_project_summary.csv",
                rows=self.build_project_summary_rows(
                    project_result=project_result,
                    storage_result=storage_result,
                    runtime_result=runtime_result
                )
            )
        )

        written_files.append(
            self.write_csv(
                file_path=exports_dir / f"{project_id}_cost_estimate.csv",
                rows=self.build_cost_rows(cost_result=cost_result)
            )
        )

        written_files.append(
            self.write_csv(
                file_path=exports_dir / f"{project_id}_planning.csv",
                rows=self.build_planning_rows(planning_result=planning_result)
            )
        )

        written_files.append(
            self.write_csv(
                file_path=exports_dir / f"{project_id}_quantity_boq.csv",
                rows=self.build_quantity_rows(quantity_result=quantity_result)
            )
        )

        written_files.append(
            self.write_csv(
                file_path=exports_dir / f"{project_id}_qa_qc.csv",
                rows=self.build_validation_rows(validation_result=validation_result)
            )
        )

        written_files.append(
            self.write_csv(
                file_path=calculations_dir / f"{project_id}_calculation_index.csv",
                rows=self.build_calculation_index_rows(
                    cost_result=cost_result,
                    planning_result=planning_result,
                    quantity_result=quantity_result,
                    validation_result=validation_result
                )
            )
        )

        self.csv_excel_result = {
            "engine": "ProjectCsvExcelExportEngine",
            "version": "1.0",
            "status": "PROJECT_CSV_EXCEL_FILES_OPGESLAGEN",
            "calculation_level": "basis CSV/Excel tabel-export",
            "project_id": project_id,
            "project_name": project_name,
            "exports_dir": str(exports_dir),
            "calculations_dir": str(calculations_dir),
            "written_files": written_files,
            "written_file_count": len(written_files),
            "cost_engine_status": cost_result.get("status", "ONBEKEND"),
            "planning_engine_status": planning_result.get("status", "ONBEKEND"),
            "quantity_engine_status": quantity_result.get("status", "ONBEKEND"),
            "validation_engine_status": validation_result.get("status", "ONBEKEND"),
            "runtime_engine_status": runtime_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(written_files),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project CSV/Excel Export Engine v1.0 maakt CSV-bestanden die direct "
                "in Excel geopend kunnen worden. In een volgende versie kan echte XLSX-export "
                "met meerdere werkbladen, opmaak, filters en formules worden toegevoegd."
            )
        }

        return self.csv_excel_result

    def write_csv(self, file_path, rows):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file, delimiter=";")
                for row in rows:
                    writer.writerow(row)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                "row_count": len(rows)
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "row_count": 0,
                "error": str(error)
            }

    def build_project_summary_rows(
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

    def build_calculation_index_rows(
        self,
        cost_result,
        planning_result,
        quantity_result,
        validation_result
    ):
        return [
            ["Berekening / tabel", "Bron-engine", "Status", "Opmerking"],
            ["Kostenraming", "Cost Estimate Engine", cost_result.get("status", "ONBEKEND"), "CSV-export in 09_exports"],
            ["Planning", "Planning Engine", planning_result.get("status", "ONBEKEND"), "CSV-export in 09_exports"],
            ["Hoeveelhedenstaat", "Quantity / BOQ Engine", quantity_result.get("status", "ONBEKEND"), "CSV-export in 09_exports"],
            ["QA/QC", "Validation & QA/QC Engine", validation_result.get("status", "ONBEKEND"), "CSV-export in 09_exports"],
            ["Indexdatum", "Project CSV/Excel Export Engine", datetime.now().isoformat(timespec="seconds"), ""]
        ]

    def build_warnings(self, written_files):
        warnings = []

        for file_info in written_files:
            if file_info.get("status") != "OPGESLAGEN":
                warnings.append(
                    f"CSV-bestand niet opgeslagen: {file_info.get('path')}"
                )

        if not warnings:
            warnings.append("Geen kritieke CSV/Excel-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_CSV_EXCEL_EXPORT_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste tabel-exportlaag. "
                "De volgende stap is echte XLSX-export met meerdere tabbladen, filters, "
                "opmaak, formules en projectdashboards."
            ),
            "next_steps": [
                "ProjectCsvExcelExportEngine koppelen aan BAOEES Core",
                "CSV-bestanden opnemen in ZIP-export",
                "echte XLSX-export toevoegen",
                "kostenraming koppelen aan hoeveelheden",
                "planning koppelen aan uitvoeringsfasen",
                "QA/QC dashboard toevoegen",
                "Excel-dashboard per project genereren"
            ]
        }

    def get_csv_excel_result(self):
        return self.csv_excel_result

    def run(self):
        print("Project CSV/Excel Export Engine actief")