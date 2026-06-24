import html
from datetime import datetime
from pathlib import Path


class ProjectHtmlDashboardExportEngine:

    def __init__(self):
        self.html_dashboard_result = {}

    def export_project_dashboard(
        self,
        project_result=None,
        storage_result=None,
        report_writer_result=None,
        pdf_docx_result=None,
        dxf_writer_result=None,
        drawing_pdf_result=None,
        csv_excel_result=None,
        xlsx_result=None,
        validation_result=None,
        runtime_result=None,
        zip_result=None
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        report_writer_result = report_writer_result or {}
        pdf_docx_result = pdf_docx_result or {}
        dxf_writer_result = dxf_writer_result or {}
        drawing_pdf_result = drawing_pdf_result or {}
        csv_excel_result = csv_excel_result or {}
        xlsx_result = xlsx_result or {}
        validation_result = validation_result or {}
        runtime_result = runtime_result or {}
        zip_result = zip_result or {}

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

        dashboard_path = exports_dir / f"{project_id}_dashboard.html"

        html_content = self.build_dashboard_html(
            project_id=project_id,
            project_name=project_name,
            project_result=project_result,
            storage_result=storage_result,
            report_writer_result=report_writer_result,
            pdf_docx_result=pdf_docx_result,
            dxf_writer_result=dxf_writer_result,
            drawing_pdf_result=drawing_pdf_result,
            csv_excel_result=csv_excel_result,
            xlsx_result=xlsx_result,
            validation_result=validation_result,
            runtime_result=runtime_result,
            zip_result=zip_result
        )

        dashboard_file_result = self.write_html_file(
            file_path=dashboard_path,
            content=html_content
        )

        self.html_dashboard_result = {
            "engine": "ProjectHtmlDashboardExportEngine",
            "version": "1.0",
            "status": "PROJECT_HTML_DASHBOARD_OPGESLAGEN",
            "calculation_level": "basis HTML projectdashboard",
            "project_id": project_id,
            "project_name": project_name,
            "exports_dir": str(exports_dir),
            "dashboard_file": dashboard_file_result,
            "report_writer_status": report_writer_result.get("status", "ONBEKEND"),
            "pdf_docx_status": pdf_docx_result.get("status", "ONBEKEND"),
            "dxf_writer_status": dxf_writer_result.get("status", "ONBEKEND"),
            "drawing_pdf_status": drawing_pdf_result.get("status", "ONBEKEND"),
            "csv_excel_status": csv_excel_result.get("status", "ONBEKEND"),
            "xlsx_status": xlsx_result.get("status", "ONBEKEND"),
            "validation_status": validation_result.get("status", "ONBEKEND"),
            "runtime_status": runtime_result.get("status", "ONBEKEND"),
            "zip_status": zip_result.get("status", "ONBEKEND"),
            "warnings": self.build_warnings(dashboard_file_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project HTML Dashboard Export Engine v1.0 maakt een lokaal HTML-dashboard. "
                "De links verwijzen naar projectbestanden binnen dezelfde projectmap. "
                "Latere versies kunnen filters, kaarten, grafieken, 3D-viewer en live Digital Twin-koppelingen toevoegen."
            )
        }

        return self.html_dashboard_result

    def write_html_file(self, file_path, content):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_dashboard_html(
        self,
        project_id,
        project_name,
        project_result,
        storage_result,
        report_writer_result,
        pdf_docx_result,
        dxf_writer_result,
        drawing_pdf_result,
        csv_excel_result,
        xlsx_result,
        validation_result,
        runtime_result,
        zip_result
    ):
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                f"outputs/projects/{project_id}"
            )
        )

        exports_dir = Path(
            storage_result.get("folder_structure", {}).get(
                "exports",
                project_output_dir / "09_exports"
            )
        )

        links = self.build_file_links(
            project_id=project_id,
            project_output_dir=project_output_dir,
            exports_dir=exports_dir,
            report_writer_result=report_writer_result,
            pdf_docx_result=pdf_docx_result,
            dxf_writer_result=dxf_writer_result,
            drawing_pdf_result=drawing_pdf_result,
            csv_excel_result=csv_excel_result,
            xlsx_result=xlsx_result,
            zip_result=zip_result
        )

        status_cards = [
            ("Markdown/TXT rapport", report_writer_result.get("status", "ONBEKEND")),
            ("PDF/DOCX rapport", pdf_docx_result.get("status", "ONBEKEND")),
            ("DXF tekeningen", dxf_writer_result.get("status", "ONBEKEND")),
            ("PDF tekeningen", drawing_pdf_result.get("status", "ONBEKEND")),
            ("CSV/Excel-tabellen", csv_excel_result.get("status", "ONBEKEND")),
            ("XLSX werkboek", xlsx_result.get("status", "ONBEKEND")),
            ("QA/QC validatie", validation_result.get("status", "ONBEKEND")),
            ("Runtime log", runtime_result.get("status", "ONBEKEND")),
            ("ZIP export", zip_result.get("status", "ONBEKEND"))
        ]

        return f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <title>BAOEES Dashboard - {self.esc(project_name)}</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0f172a;
            color: #e5e7eb;
        }}

        header {{
            padding: 32px;
            background: linear-gradient(135deg, #111827, #1e3a8a);
            border-bottom: 1px solid #334155;
        }}

        header h1 {{
            margin: 0;
            font-size: 32px;
        }}

        header p {{
            margin: 8px 0 0 0;
            color: #cbd5e1;
        }}

        main {{
            padding: 28px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px;
            margin-bottom: 28px;
        }}

        .card {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
        }}

        .card h2 {{
            margin: 0 0 12px 0;
            font-size: 18px;
            color: #93c5fd;
        }}

        .status {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #064e3b;
            color: #d1fae5;
            font-size: 12px;
            font-weight: bold;
        }}

        .status.unknown {{
            background: #78350f;
            color: #ffedd5;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #111827;
            border: 1px solid #334155;
            border-radius: 12px;
            overflow: hidden;
        }}

        th, td {{
            padding: 12px;
            border-bottom: 1px solid #334155;
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background: #1f2937;
            color: #bfdbfe;
        }}

        a {{
            color: #93c5fd;
            text-decoration: none;
            font-weight: bold;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .small {{
            color: #94a3b8;
            font-size: 13px;
        }}

        footer {{
            padding: 24px 28px;
            color: #94a3b8;
            border-top: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <header>
        <h1>BAOEES Projectdashboard</h1>
        <p>{self.esc(project_name)} | Project-ID: {self.esc(project_id)}</p>
    </header>

    <main>
        <section class="grid">
            <div class="card">
                <h2>Project</h2>
                <p><strong>Naam:</strong> {self.esc(project_result.get("project_name", "Onbekend"))}</p>
                <p><strong>Type:</strong> {self.esc(project_result.get("project_type", "Onbekend"))}</p>
                <p><strong>Locatie:</strong> {self.esc(project_result.get("location", "Onbekend"))}</p>
                <p><strong>Land:</strong> {self.esc(project_result.get("country", "Onbekend"))}</p>
            </div>

            <div class="card">
                <h2>Runtime</h2>
                <p><strong>Mode:</strong> {self.esc(project_result.get("runtime_mode", "onbekend"))}</p>
                <p><strong>Status:</strong> {self.esc(runtime_result.get("status", "ONBEKEND"))}</p>
                <p><strong>Datum:</strong> {datetime.now().isoformat(timespec="seconds")}</p>
            </div>

            <div class="card">
                <h2>QA/QC</h2>
                <p><strong>Status:</strong> {self.esc(validation_result.get("status", "ONBEKEND"))}</p>
                <p><strong>Go/No-Go:</strong> {self.esc(validation_result.get("go_no_go_advice", "Niet beschikbaar"))}</p>
            </div>

            <div class="card">
                <h2>Projectmap</h2>
                <p class="small">{self.esc(str(project_output_dir))}</p>
            </div>
        </section>

        <section>
            <h2>Engine status</h2>
            <div class="grid">
                {self.status_cards_html(status_cards)}
            </div>
        </section>

        <section>
            <h2>Projectbestanden openen</h2>
            <table>
                <thead>
                    <tr>
                        <th>Categorie</th>
                        <th>Bestand</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
                    {self.links_table_html(links)}
                </tbody>
            </table>
        </section>
    </main>

    <footer>
        BAOEES V3 HTML Dashboard Export Engine v1.0 — automatisch gegenereerd dashboard.
    </footer>
</body>
</html>
"""

    def build_file_links(
        self,
        project_id,
        project_output_dir,
        exports_dir,
        report_writer_result,
        pdf_docx_result,
        dxf_writer_result,
        drawing_pdf_result,
        csv_excel_result,
        xlsx_result,
        zip_result
    ):
        project_output_dir = Path(project_output_dir)

        default_files = [
            ("Rapport", f"{project_id}_project_report.md", project_output_dir / "01_reports" / f"{project_id}_project_report.md"),
            ("Rapport", f"{project_id}_project_report.txt", project_output_dir / "01_reports" / f"{project_id}_project_report.txt"),
            ("Rapport", f"{project_id}_project_report.pdf", project_output_dir / "01_reports" / f"{project_id}_project_report.pdf"),
            ("Rapport", f"{project_id}_project_report.docx", project_output_dir / "01_reports" / f"{project_id}_project_report.docx"),
            ("PDF-tekening", f"{project_id}_situatie.pdf", project_output_dir / "02_drawings" / f"{project_id}_situatie.pdf"),
            ("PDF-tekening", f"{project_id}_plattegrond.pdf", project_output_dir / "02_drawings" / f"{project_id}_plattegrond.pdf"),
            ("PDF-tekening", f"{project_id}_doorsnede.pdf", project_output_dir / "02_drawings" / f"{project_id}_doorsnede.pdf"),
            ("DXF", f"{project_id}_situatie.dxf", project_output_dir / "03_cad" / f"{project_id}_situatie.dxf"),
            ("DXF", f"{project_id}_plattegrond.dxf", project_output_dir / "03_cad" / f"{project_id}_plattegrond.dxf"),
            ("DXF", f"{project_id}_doorsnede.dxf", project_output_dir / "03_cad" / f"{project_id}_doorsnede.dxf"),
            ("CSV", f"{project_id}_project_summary.csv", project_output_dir / "09_exports" / f"{project_id}_project_summary.csv"),
            ("CSV", f"{project_id}_cost_estimate.csv", project_output_dir / "09_exports" / f"{project_id}_cost_estimate.csv"),
            ("CSV", f"{project_id}_planning.csv", project_output_dir / "09_exports" / f"{project_id}_planning.csv"),
            ("CSV", f"{project_id}_quantity_boq.csv", project_output_dir / "09_exports" / f"{project_id}_quantity_boq.csv"),
            ("CSV", f"{project_id}_qa_qc.csv", project_output_dir / "09_exports" / f"{project_id}_qa_qc.csv"),
            ("XLSX", f"{project_id}_project_tables.xlsx", project_output_dir / "09_exports" / f"{project_id}_project_tables.xlsx"),
            ("JSON", "digital_twin.json", project_output_dir / "07_digital_twin" / "digital_twin.json"),
            ("JSON", "source_register.json", project_output_dir / "06_sources" / "source_register.json"),
            ("JSON", "runtime_log.json", project_output_dir / "08_runtime_logs" / "runtime_log.json"),
            ("ZIP", f"{project_id}_project_export.zip", project_output_dir / "10_zip" / f"{project_id}_project_export.zip")
        ]

        links = []

        for category, filename, path in default_files:
            links.append({
                "category": category,
                "filename": filename,
                "path": str(path),
                "href": self.relative_href(from_dir=exports_dir, to_path=path),
                "exists": Path(path).exists()
            })

        return links

    def relative_href(self, from_dir, to_path):
        try:
            return Path(to_path).resolve().relative_to(Path(from_dir).resolve()).as_posix()
        except Exception:
            try:
                return Path(to_path).resolve().as_uri()
            except Exception:
                return str(to_path)

    def status_cards_html(self, status_cards):
        html_parts = []

        for title, status in status_cards:
            status_text = self.esc(status)
            css_class = "status"

            if status in ["ONBEKEND", "", None]:
                css_class = "status unknown"

            html_parts.append(
                f"""
                <div class="card">
                    <h2>{self.esc(title)}</h2>
                    <span class="{css_class}">{status_text}</span>
                </div>
                """
            )

        return "\n".join(html_parts)

    def links_table_html(self, links):
        rows = []

        for link in links:
            exists_text = "Openen" if link.get("exists") else "Nog niet gevonden"
            href = self.esc(link.get("href", "#"))
            filename = self.esc(link.get("filename", "bestand"))
            category = self.esc(link.get("category", "Bestand"))

            if link.get("exists"):
                link_html = f'<a href="{href}">{exists_text}</a>'
            else:
                link_html = f'<span class="small">{exists_text}</span>'

            rows.append(
                f"""
                <tr>
                    <td>{category}</td>
                    <td>{filename}</td>
                    <td>{link_html}</td>
                </tr>
                """
            )

        return "\n".join(rows)

    def esc(self, value):
        return html.escape(str(value))

    def build_warnings(self, dashboard_file_result):
        warnings = []

        if dashboard_file_result.get("status") != "OPGESLAGEN":
            warnings.append("HTML-dashboard is niet opgeslagen.")

        if not warnings:
            warnings.append("Geen kritieke HTML-dashboardexportwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_HTML_DASHBOARD_ADVIES",
            "advice": (
                "Gebruik deze engine als eerste lokaal projectdashboard. "
                "De volgende stap is uitbreiding met live status, grafieken, kaarten, "
                "3D-viewer en Digital Twin-objectweergave."
            ),
            "next_steps": [
                "ProjectHtmlDashboardExportEngine koppelen aan BAOEES Core",
                "HTML-dashboard opnemen in ZIP-export",
                "links naar alle outputbestanden controleren",
                "projectstatus visueel uitbreiden",
                "grafieken toevoegen",
                "kaartviewer toevoegen",
                "Digital Twin-viewer toevoegen",
                "dashboard als startpagina van projectexport gebruiken"
            ]
        }

    def get_html_dashboard_result(self):
        return self.html_dashboard_result

    def run(self):
        print("Project HTML Dashboard Export Engine actief")