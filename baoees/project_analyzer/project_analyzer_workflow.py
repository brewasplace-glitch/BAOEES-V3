from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from baoees.project_analyzer.bib_context_loader import ProjectAnalyzerBibContextLoader
from baoees.project_analyzer.aaie_bib_assumption_loader import AaieBibAssumptionLoader
from baoees.project_analyzer.geo_foundation_bib_engine import GeoFoundationBibEngine
from baoees.project_analyzer.project_report_bib_engine import ProjectReportBibEngine
from baoees.project_analyzer.project_report_export_engine import ProjectReportExportEngine
from baoees.project_analyzer.project_package_evidence_engine import ProjectPackageEvidenceEngine


class ProjectAnalyzerWorkflow:
    """
    PROJECT PHOENIX / BAOEES
    Project Analyzer Workflow v4.6

    Doel:
    - Centrale workflow voor Project Analyzer.
    - Laadt BIB-context.
    - Genereert AAIE-aannames.
    - Genereert Geo/Foundation analyse.
    - Genereert projectrapport.
    - Exporteert DOCX/PDF.
    - Genereert Project ZIP / Evidence pakket.
    """

    ENGINE_NAME = "Project Phoenix Project Analyzer Workflow"
    ENGINE_VERSION = "v4.6"

    def __init__(
        self,
        project_output_root: Optional[str | Path] = None,
        bib_output_root: Optional[str | Path] = None,
    ) -> None:
        self.project_output_root = (
            Path(project_output_root)
            if project_output_root
            else Path("outputs") / "projects"
        )

        self.bib_output_root = (
            Path(bib_output_root)
            if bib_output_root
            else Path("outputs") / "bib"
        )

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)
        self.bib_output_root.mkdir(parents=True, exist_ok=True)

        workflow_log_path = self.project_output_root / "project_analyzer_workflow_log.json"
        workflow_dashboard_path = self.project_output_root / "project_analyzer_workflow_dashboard.html"

        started_at = datetime.now().isoformat(timespec="seconds")

        steps: Dict[str, Any] = {}

        bib_context_result = self.run_step(
            step_key="bib_context",
            step_name="BIB-context laden",
            runner=lambda: ProjectAnalyzerBibContextLoader(
                project_output_root=self.project_output_root,
                bib_output_root=self.bib_output_root,
            ).run(),
        )
        steps["bib_context"] = bib_context_result

        aaie_result = self.run_step(
            step_key="aaie_assumptions",
            step_name="AAIE-aannames genereren",
            runner=lambda: AaieBibAssumptionLoader(
                project_output_root=self.project_output_root,
            ).run(
                bib_context_result=bib_context_result,
            ),
        )
        steps["aaie_assumptions"] = aaie_result

        geo_foundation_result = self.run_step(
            step_key="geo_foundation",
            step_name="Geo/Foundation analyse genereren",
            runner=lambda: GeoFoundationBibEngine(
                project_output_root=self.project_output_root,
            ).run(
                bib_context_result=bib_context_result,
                aaie_result=aaie_result,
            ),
        )
        steps["geo_foundation"] = geo_foundation_result

        report_result = self.run_step(
            step_key="project_report",
            step_name="Projectrapport genereren",
            runner=lambda: ProjectReportBibEngine(
                project_output_root=self.project_output_root,
            ).run(
                bib_context_result=bib_context_result,
                aaie_result=aaie_result,
                geo_foundation_result=geo_foundation_result,
            ),
        )
        steps["project_report"] = report_result

        export_result = self.run_step(
            step_key="project_report_export",
            step_name="Projectrapport exporteren naar DOCX/PDF",
            runner=lambda: ProjectReportExportEngine(
                project_output_root=self.project_output_root,
            ).run(
                bib_context_result=bib_context_result,
                aaie_result=aaie_result,
                geo_foundation_result=geo_foundation_result,
                report_result=report_result,
            ),
        )
        steps["project_report_export"] = export_result

        package_evidence_result = self.run_step(
            step_key="project_package_evidence",
            step_name="Project ZIP / Evidence pakket genereren",
            runner=lambda: ProjectPackageEvidenceEngine(
                project_output_root=self.project_output_root,
                bib_output_root=self.bib_output_root,
            ).run(
                bib_context_result=bib_context_result,
                aaie_result=aaie_result,
                geo_foundation_result=geo_foundation_result,
                report_result=report_result,
                export_result=export_result,
            ),
        )
        steps["project_package_evidence"] = package_evidence_result

        finished_at = datetime.now().isoformat(timespec="seconds")

        result = {
            "status": self.determine_workflow_status(steps),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "project_output_root": str(self.project_output_root),
            "bib_output_root": str(self.bib_output_root),
            "outputs": {
                "workflow_log_path": str(workflow_log_path),
                "workflow_dashboard_path": str(workflow_dashboard_path),
                "project_package_evidence_dashboard": str(
                    self.project_output_root / "project_package_evidence_dashboard.html"
                ),
                "project_package_manifest": str(
                    self.project_output_root / "project_package_manifest.json"
                ),
                "project_package_evidence_log": str(
                    self.project_output_root / "project_package_evidence_log.json"
                ),
                "project_zip": str(
                    self.project_output_root / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip"
                ),
            },
            "steps": steps,
            "warnings": self.collect_warnings(steps),
            "next_steps": [
                "Open project_analyzer_workflow_dashboard.html.",
                "Open project_package_evidence_dashboard.html.",
                "Controleer PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip.",
                "Controleer of centrale workflow, rapportage, export en evidencepakket aanwezig zijn.",
                "Koppel deze volledige workflow later aan de Project Phoenix launcher of startknop.",
            ],
        }

        self.write_json(workflow_log_path, result)
        workflow_dashboard_path.write_text(
            self.build_html_dashboard(result),
            encoding="utf-8",
        )

        return result

    def run_step(self, step_key: str, step_name: str, runner: Any) -> Dict[str, Any]:
        started_at = datetime.now().isoformat(timespec="seconds")

        try:
            output = runner()
            status = output.get("status", "OPGESLAGEN") if isinstance(output, dict) else "OPGESLAGEN"

            return {
                "step_key": step_key,
                "step_name": step_name,
                "status": status,
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "output": output,
            }

        except Exception as error:
            return {
                "step_key": step_key,
                "step_name": step_name,
                "status": "FAILED",
                "started_at": started_at,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "error_type": type(error).__name__,
                "error_message": str(error),
            }

    def determine_workflow_status(self, steps: Dict[str, Any]) -> str:
        statuses = [
            str(step.get("status", "")).upper()
            for step in steps.values()
        ]

        if any(status == "FAILED" for status in statuses):
            return "FAILED"

        if any(status == "FOUT" for status in statuses):
            return "FAILED"

        if any(status == "WARNING" for status in statuses):
            return "WARNING"

        return "OPGESLAGEN"

    def collect_warnings(self, steps: Dict[str, Any]) -> list[str]:
        warnings = []

        for step in steps.values():
            output = step.get("output")

            if isinstance(output, dict):
                for warning in output.get("warnings", []):
                    warnings.append(f"{step.get('step_name')}: {warning}")

            if step.get("status") == "FAILED":
                warnings.append(
                    f"{step.get('step_name')}: {step.get('error_type')} - {step.get('error_message')}"
                )

        if not warnings:
            warnings.append("Geen kritieke Project Analyzer Workflow-waarschuwingen.")

        return warnings

    def build_html_dashboard(self, result: Dict[str, Any]) -> str:
        step_cards = ""

        for step in result.get("steps", {}).values():
            status = str(step.get("status", ""))
            output = step.get("output", {})
            error_message = step.get("error_message", "")

            details = ""

            if isinstance(output, dict):
                outputs = output.get("outputs", {})
                if isinstance(outputs, dict):
                    for label, path in outputs.items():
                        details += f"<li><strong>{self.esc(label)}</strong>: <code>{self.esc(path)}</code></li>"

            if error_message:
                details += f"<li><strong>Fout</strong>: {self.esc(error_message)}</li>"

            if not details:
                details = "<li>Geen extra details.</li>"

            step_cards += f"""
            <div class="card">
              <h3>{self.esc(step.get("step_name", ""))}</h3>
              <p><strong>Status:</strong> {self.esc(status)}</p>
              <p><strong>Start:</strong> {self.esc(step.get("started_at", ""))}</p>
              <p><strong>Einde:</strong> {self.esc(step.get("finished_at", ""))}</p>
              <ul>
                {details}
              </ul>
            </div>
            """

        warning_items = ""

        for warning in result.get("warnings", []):
            warning_items += f"<li>{self.esc(warning)}</li>"

        project_package_dashboard = Path(
            result.get("outputs", {}).get("project_package_evidence_dashboard", "")
        ).name

        project_zip = Path(
            result.get("outputs", {}).get("project_zip", "")
        ).name

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
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    a {{
      color: #93c5fd;
    }}
    code {{
      color: #cbd5e1;
      word-break: break-all;
    }}
    .muted {{
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT ANALYZER WORKFLOW DASHBOARD</h1>
    <p>Project Phoenix / BAOEES centrale workflow v4.6.</p>
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
        <p class="muted">{self.esc(result.get("engine_version", ""))}</p>
      </div>
      <div class="card">
        <h3>Evidence Dashboard</h3>
        <p><a href="{self.esc(project_package_dashboard)}">{self.esc(project_package_dashboard)}</a></p>
      </div>
      <div class="card">
        <h3>Project ZIP</h3>
        <p><a href="{self.esc(project_zip)}">{self.esc(project_zip)}</a></p>
      </div>
    </section>

    <h2>Workflow stappen</h2>
    <section class="grid">
      {step_cards}
    </section>

    <h2>Waarschuwingen</h2>
    <ul>
      {warning_items}
    </ul>
  </main>
</body>
</html>
"""

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def esc(self, value: Any) -> str:
        import html

        return html.escape(str(value), quote=True)


def main() -> None:
    workflow = ProjectAnalyzerWorkflow()
    result = workflow.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()