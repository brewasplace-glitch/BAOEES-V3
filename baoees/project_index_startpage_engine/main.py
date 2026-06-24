import html
import json
from datetime import datetime
from pathlib import Path


class ProjectIndexStartpageEngine:

    def __init__(self):
        self.index_result = {}

    def create_project_index(
        self,
        projects_root="outputs/projects",
        project_index_path="configs/projects/project_index.json"
    ):
        projects_root = Path(projects_root)
        project_index_path = Path(project_index_path)

        projects_root.mkdir(parents=True, exist_ok=True)

        projects = self.load_projects_from_config(
            project_index_path=project_index_path
        )

        if not projects:
            projects = self.discover_projects_from_output(
                projects_root=projects_root
            )

        index_path = projects_root / "index.html"

        html_content = self.build_index_html(
            projects=projects,
            projects_root=projects_root,
            project_index_path=project_index_path
        )

        index_file_result = self.write_html_file(
            file_path=index_path,
            content=html_content
        )

        self.index_result = {
            "engine": "ProjectIndexStartpageEngine",
            "version": "1.0",
            "status": "PROJECT_INDEX_STARTPAGE_OPGESLAGEN",
            "calculation_level": "centrale HTML projectstartpagina",
            "projects_root": str(projects_root),
            "project_index_path": str(project_index_path),
            "index_file": index_file_result,
            "project_count": len(projects),
            "projects": projects,
            "warnings": self.build_warnings(index_file_result, projects),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Index / Startpage Engine v1.0 maakt een centrale lokale "
                "HTML-startpagina voor alle BAOEES-projecten. Latere versies kunnen live "
                "status, zoekfunctie, filters, thumbnails, gebruikersrechten en dashboardwidgets toevoegen."
            )
        }

        return self.index_result

    def load_projects_from_config(self, project_index_path):
        if not project_index_path.exists():
            return []

        try:
            with open(project_index_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            projects = data.get("projects", [])

            normalized_projects = []

            for project in projects:
                if isinstance(project, dict):
                    project_id = (
                        project.get("project_id")
                        or project.get("id")
                        or project.get("name")
                        or "unknown_project"
                    )

                    normalized_projects.append({
                        "project_id": project_id,
                        "project_name": project.get("project_name", project_id),
                        "project_type": project.get("project_type", "Onbekend"),
                        "location": project.get("location", "Onbekend"),
                        "country": project.get("country", "Onbekend"),
                        "config_path": project.get("config_path", "")
                    })

            return normalized_projects

        except Exception:
            return []

    def discover_projects_from_output(self, projects_root):
        projects = []

        if not projects_root.exists():
            return projects

        for child in projects_root.iterdir():
            if child.is_dir():
                project_id = child.name

                projects.append({
                    "project_id": project_id,
                    "project_name": project_id.replace("_", " ").title(),
                    "project_type": "Onbekend",
                    "location": "Onbekend",
                    "country": "Onbekend",
                    "config_path": ""
                })

        return projects

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

    def build_index_html(
        self,
        projects,
        projects_root,
        project_index_path
    ):
        project_cards = self.build_project_cards_html(
            projects=projects,
            projects_root=projects_root
        )

        return f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <title>BAOEES Project Index</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #020617;
            color: #e5e7eb;
        }}

        header {{
            padding: 34px;
            background: linear-gradient(135deg, #0f172a, #1d4ed8);
            border-bottom: 1px solid #334155;
        }}

        header h1 {{
            margin: 0;
            font-size: 34px;
        }}

        header p {{
            margin: 10px 0 0 0;
            color: #cbd5e1;
        }}

        main {{
            padding: 30px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
            margin-bottom: 28px;
        }}

        .card {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
        }}

        .card h2 {{
            margin: 0 0 12px 0;
            color: #93c5fd;
            font-size: 20px;
        }}

        .project-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
            gap: 20px;
        }}

        .project-card {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.24);
        }}

        .project-card h2 {{
            margin: 0 0 10px 0;
            color: #bfdbfe;
        }}

        .small {{
            color: #94a3b8;
            font-size: 13px;
        }}

        .status {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #064e3b;
            color: #d1fae5;
            font-size: 12px;
            font-weight: bold;
            margin: 8px 0 12px 0;
        }}

        .status.warning {{
            background: #78350f;
            color: #ffedd5;
        }}

        a {{
            color: #93c5fd;
            text-decoration: none;
            font-weight: bold;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        ul {{
            margin: 10px 0 0 0;
            padding-left: 18px;
        }}

        li {{
            margin: 8px 0;
        }}

        footer {{
            padding: 24px 30px;
            border-top: 1px solid #334155;
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <header>
        <h1>BAOEES Project Index</h1>
        <p>Centrale startpagina voor alle BAOEES V3-projecten</p>
    </header>

    <main>
        <section class="summary">
            <div class="card">
                <h2>Projecten</h2>
                <p><strong>Aantal:</strong> {len(projects)}</p>
            </div>

            <div class="card">
                <h2>Projectmap</h2>
                <p class="small">{self.esc(str(projects_root))}</p>
            </div>

            <div class="card">
                <h2>Projectindex config</h2>
                <p class="small">{self.esc(str(project_index_path))}</p>
            </div>

            <div class="card">
                <h2>Gegenereerd</h2>
                <p>{datetime.now().isoformat(timespec="seconds")}</p>
            </div>
        </section>

        <section>
            <h2>Projectdashboards</h2>
            <div class="project-grid">
                {project_cards}
            </div>
        </section>
    </main>

    <footer>
        BAOEES V3 Project Index / Startpage Engine v1.0 — automatisch gegenereerd.
    </footer>
</body>
</html>
"""

    def build_project_cards_html(self, projects, projects_root):
        cards = []

        for project in projects:
            project_id = project.get("project_id", "unknown_project")
            project_name = project.get("project_name", project_id)
            project_type = project.get("project_type", "Onbekend")
            location = project.get("location", "Onbekend")
            country = project.get("country", "Onbekend")

            project_dir = Path(projects_root) / project_id

            dashboard_path = (
                project_dir
                / "09_exports"
                / f"{project_id}_dashboard.html"
            )

            zip_path = (
                project_dir
                / "10_zip"
                / f"{project_id}_project_export.zip"
            )

            report_pdf_path = (
                project_dir
                / "01_reports"
                / f"{project_id}_project_report.pdf"
            )

            xlsx_path = (
                project_dir
                / "09_exports"
                / f"{project_id}_project_tables.xlsx"
            )

            dashboard_exists = dashboard_path.exists()
            zip_exists = zip_path.exists()

            status_class = "status" if dashboard_exists and zip_exists else "status warning"
            status_text = "PROJECT EXPORT GEREED" if dashboard_exists and zip_exists else "PROJECT EXPORT ONVOLLEDIG"

            dashboard_link = self.link_or_missing(
                label="Open projectdashboard",
                path=dashboard_path,
                from_dir=projects_root
            )

            zip_link = self.link_or_missing(
                label="Open project-ZIP",
                path=zip_path,
                from_dir=projects_root
            )

            report_link = self.link_or_missing(
                label="Open PDF-rapport",
                path=report_pdf_path,
                from_dir=projects_root
            )

            xlsx_link = self.link_or_missing(
                label="Open Excel-werkboek",
                path=xlsx_path,
                from_dir=projects_root
            )

            cards.append(
                f"""
                <div class="project-card">
                    <h2>{self.esc(project_name)}</h2>
                    <span class="{status_class}">{status_text}</span>
                    <p><strong>Project-ID:</strong> {self.esc(project_id)}</p>
                    <p><strong>Type:</strong> {self.esc(project_type)}</p>
                    <p><strong>Locatie:</strong> {self.esc(location)}, {self.esc(country)}</p>
                    <ul>
                        <li>{dashboard_link}</li>
                        <li>{zip_link}</li>
                        <li>{report_link}</li>
                        <li>{xlsx_link}</li>
                    </ul>
                </div>
                """
            )

        if not cards:
            return """
            <div class="project-card">
                <h2>Geen projecten gevonden</h2>
                <p>Er zijn nog geen projectmappen of projectconfiguraties gevonden.</p>
            </div>
            """

        return "\n".join(cards)

    def link_or_missing(self, label, path, from_dir):
        path = Path(path)

        if path.exists():
            href = self.relative_href(from_dir=from_dir, to_path=path)
            return f'<a href="{self.esc(href)}">{self.esc(label)}</a>'

        return f'<span class="small">{self.esc(label)} — nog niet gevonden</span>'

    def relative_href(self, from_dir, to_path):
        try:
            return Path(to_path).resolve().relative_to(Path(from_dir).resolve()).as_posix()
        except Exception:
            try:
                return Path(to_path).resolve().as_uri()
            except Exception:
                return str(to_path)

    def esc(self, value):
        return html.escape(str(value))

    def build_warnings(self, index_file_result, projects):
        warnings = []

        if index_file_result.get("status") != "OPGESLAGEN":
            warnings.append("Projectindex startpagina is niet opgeslagen.")

        if not projects:
            warnings.append("Geen projecten gevonden voor projectindex.")

        if not warnings:
            warnings.append("Geen kritieke projectindexwaarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_INDEX_STARTPAGE_ADVIES",
            "advice": (
                "Gebruik deze engine als centrale startpagina voor lokale projectoutput. "
                "De volgende stap is koppeling aan live projectstatus, zoekfunctie, filters "
                "en een echte BAOEES desktop/web interface."
            ),
            "next_steps": [
                "ProjectIndexStartpageEngine koppelen aan BAOEES Core",
                "index.html automatisch na iedere projectrun bijwerken",
                "projectstatus uit runtime logs lezen",
                "laatste wijzigingsdatum per project tonen",
                "zoek- en filterfunctie toevoegen",
                "dashboardkaarten uitbreiden",
                "BAOEES startscherm koppelen aan index.html"
            ]
        }

    def get_index_result(self):
        return self.index_result

    def run(self):
        print("Project Index / Startpage Engine actief")