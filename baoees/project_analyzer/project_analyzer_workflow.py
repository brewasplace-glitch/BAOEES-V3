from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.project_analyzer.bib_context_loader import ProjectAnalyzerBibContextLoader
from baoees.project_analyzer.aaie_bib_assumption_loader import AaieBibAssumptionLoader
from baoees.project_analyzer.geo_foundation_bib_engine import GeoFoundationBibEngine
from baoees.project_analyzer.project_report_bib_engine import ProjectReportBibEngine
from baoees.project_analyzer.project_report_export_engine import ProjectReportExportEngine


class ProjectAnalyzerWorkflow:
    """
    PROJECT PHOENIX / BAOEES
    Project Analyzer Workflow v4.3

    Doel:
    - BIB-context laden.
    - AAIE-aannames laden.
    - Geo/Fundering analyse draaien.
    - Projectrapport opbouwen.
    - Projectrapport exporteren naar DOCX/PDF.
    - Workflow-log en HTML-dashboard maken.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer Workflow"
    ENGINE_VERSION = "v4.3"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

    def run(
        self,
        project_context: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False,
        **extra_results: Any,
    ) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        project_context = project_context or self.default_project_context()

        started_at = datetime.now().isoformat(timespec="seconds")

        bib_context_result = ProjectAnalyzerBibContextLoader(
            project_output_root=self.project_output_root
        ).run(
            project_context=project_context,
            force_refresh_bridge=force_refresh,
        )

        aaie_result = AaieBibAssumptionLoader(
            project_output_root=self.project_output_root
        ).run(
            project_context=project_context,
            force_refresh_context=force_refresh,
        )

        geo_result = GeoFoundationBibEngine(
            project_output_root=self.project_output_root
        ).run(
            project_context=project_context,
            force_refresh_assumptions=force_refresh,
        )

        report_result = ProjectReportBibEngine(
            project_output_root=self.project_output_root
        ).run(
            project_context=project_context,
            force_refresh_geo=force_refresh,
        )

        export_result = ProjectReportExportEngine(
            project_output_root=self.project_output_root
        ).run(
            project_context=project_context,
            force_refresh_report=force_refresh,
        )

        workflow_log_path = self.project_output_root / "project_analyzer_workflow_log.json"
        workflow_dashboard_path = self.project_output_root / "project_analyzer_workflow_dashboard.html"

        result = {
            "status": self.determine_status(
                [
                    bib_context_result,
                    aaie_result,
                    geo_result,
                    report_result,
                    export_result,
                ]
            ),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Volledige Project Analyzer hoofdworkflow draaien.",
            "project_context": project_context,
            "project_output_root": str(self.project_output_root),
            "workflow_steps": [
                {
                    "step": 1,
                    "name": "BIB-context laden",
                    "result": bib_context_result,
                },
                {
                    "step": 2,
                    "name": "AAIE-aannames laden",
                    "result": aaie_result,
                },
                {
                    "step": 3,
                    "name": "Geo/Fundering analyse",
                    "result": geo_result,
                },
                {
                    "step": 4,
                    "name": "Projectrapport opbouwen",
                    "result": report_result,
                },
                {
                    "step": 5,
                    "name": "Projectrapport exporteren",
                    "result": export_result,
                },
            ],
            "outputs": {
                "workflow_log_path": str(workflow_log_path),
                "workflow_dashboard_path": str(workflow_dashboard_path),
                "bib_context": str(self.project_output_root / "project_analyzer_bib_context.json"),
                "aaie_assumptions": str(self.project_output_root / "aaie_bib_assumptions.json"),
                "geo_foundation_analysis": str(self.project_output_root / "geo_foundation_bib_analysis.json"),
                "project_report_package": str(self.project_output_root / "project_report_bib_package.json"),
                "project_report_docx": str(self.project_output_root / "project_report_bib_report.docx"),
                "project_report_pdf": str(self.project_output_root / "project_report_bib_report.pdf"),
                "project_report_export_dashboard": str(self.project_output_root / "project_report_export_dashboard.html"),
            },
            "warnings": self.build_warnings(
                [
                    bib_context_result,
                    aaie_result,
                    geo_result,
                    report_result,
                    export_result,
                ]
            ),
            "next_steps": [
                "Koppel deze workflow in v4.4 aan de Project Phoenix Launcher.",
                "Laat ieder nieuw project standaard via deze workflow starten.",
                "Voeg later project-specifieke input toe via locatie, tekst, kaartuitsnede of upload.",
                "Voeg later professionele rapportopmaak en bijlagen toe.",
                "Voeg later Project ZIP en Git Evidence automatisch toe.",
            ],
            "extra_results": extra_results,
        }

        self.write_json(workflow_log_path, result)
        workflow_dashboard_path.write_text(
            self.build_html_dashboard(result),
            encoding="utf-8",
        )

        return result

    def determine_status(self, step_results: List[Dict[str, Any]]) -> str:
        failed_statuses = {"FAILED", "FOUT", "ERROR"}
        warning_statuses = {"WARNING", "WAARSCHUWING"}

        for result in step_results:
            if result.get("status") in failed_statuses:
                return "FAILED"

        for result in step_results:
            if result.get("status") in warning_statuses:
                return "WARNING"

        return "OPGESLAGEN"

    def build_warnings(self, step_results: List[Dict[str, Any]]) -> List[str]:
        warnings: List[str] = []

        for result in step_results:
            engine = result.get("engine", "onbekende engine")
            status = result.get("status", "onbekend")

            if status not in {"OPGESLAGEN", "GEREED"}:
                warnings.append(f"{engine}: status is {status}")

            for warning in result.get("warnings", []):
                warning_text = str(warning)

                if "Geen kritieke" not in warning_text:
                    warnings.append(f"{engine}: {warning_text}")

        required_outputs = [
            self.project_output_root / "project_analyzer_bib_context.json",
            self.project_output_root / "aaie_bib_assumptions.json",
            self.project_output_root / "geo_foundation_bib_analysis.json",
            self.project_output_root / "project_report_bib_package.json",
            self.project_output_root / "project_report_bib_report.docx",
            self.project_output_root / "project_report_bib_report.pdf",
            self.project_output_root / "project_report_export_dashboard.html",
        ]

        for path in required_outputs:
            if not path.exists():
                warnings.append(f"Verplichte workflow-output ontbreekt: {path}")

        if not warnings:
            warnings.append("Geen kritieke Project Analyzer Workflow-waarschuwingen.")

        return warnings

    def build_html_dashboard(self, result: Dict[str, Any]) -> str:
        step_rows = ""

        for step in result.get("workflow_steps", []):
            step_result = step.get("result", {})
            step_rows += (
                "<tr>"
                f"<td>{self.esc(step.get('step', ''))}</td>"
                f"<td>{self.esc(step.get('name', ''))}</td>"
                f"<td>{self.esc(step_result.get('engine', ''))}</td>"
                f"<td>{self.esc(step_result.get('status', ''))}</td>"
                "</tr>"
            )

        output_rows = ""

        for name, path in result.get("outputs", {}).items():
            output_rows += (
                "<tr>"
                f"<td>{self.esc(name)}</td>"
                f"<td>{self.esc(path)}</td>"
                f"<td>{self.esc(Path(path).exists())}</td>"
                "</tr>"
            )

        warning_items = ""

        for warning in result.get("warnings", []):
            warning_items += f"<li>{self.esc(warning)}</li>"

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Analyzer Workflow Dashboard</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #050816;
      color: #f8fafc;
      line-height: 1.5;
    }}
    header {{
      padding: 34px 42px;
      background: #0f172a;
      border-bottom: 1px solid #334155;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      margin-top: 18px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0f172a;
      color: #bfdbfe;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT ANALYZER WORKFLOW DASHBOARD</h1>
    <p>Project Phoenix / BAOEES hoofdworkflow v4.3.</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p>{self.esc(result.get("status", ""))}</p>
      </div>
      <div class="card">
        <h3>Engine</h3>
        <p>{self.esc(result.get("engine", ""))}</p>
      </div>
      <div class="card">
        <h3>Versie</h3>
        <p>{self.esc(result.get("engine_version", ""))}</p>
      </div>
      <div class="card">
        <h3>Project output</h3>
        <p class="muted">{self.esc(result.get("project_output_root", ""))}</p>
      </div>
    </section>

    <h2>Workflow stappen</h2>
    <table>
      <thead>
        <tr>
          <th>Stap</th>
          <th>Naam</th>
          <th>Engine</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {step_rows}
      </tbody>
    </table>

    <h2>Outputs</h2>
    <table>
      <thead>
        <tr>
          <th>Naam</th>
          <th>Pad</th>
          <th>Bestaat</th>
        </tr>
      </thead>
      <tbody>
        {output_rows}
      </tbody>
    </table>

    <h2>Waarschuwingen</h2>
    <ul>
      {warning_items}
    </ul>
  </main>
</body>
</html>
"""

    def default_project_context(self) -> Dict[str, Any]:
        return {
            "project_name": "Default Project Phoenix Analyzer Workflow",
            "project_type": "bouw",
            "purpose": "Volledige BAOEES projectanalyse via BIB, AAIE, Geo/Foundation en rapportexport.",
            "phase": "concept",
        }

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    workflow = ProjectAnalyzerWorkflow()
    result = workflow.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()