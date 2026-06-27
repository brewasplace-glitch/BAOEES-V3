from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from baoees.project_analyzer.project_analyzer_workflow import ProjectAnalyzerWorkflow
from baoees.project_analyzer.project_analyzer_launcher_bridge import ProjectAnalyzerLauncherBridge


class ProjectStartAnalysisEngine:
    """
    PROJECT PHOENIX / BAOEES
    Project Start Analysis Engine v5.0

    Doel:
    - Vormt het centrale startpunt voor START PROJECTANALYSE.
    - Draait de centrale Project Analyzer Workflow.
    - Genereert rapportage, DOCX/PDF, Project ZIP, manifest en evidence dashboard via de workflow.
    - Werkt daarna de Project Phoenix Launcher bij.
    - Maakt een startlog en startdashboard.
    - Print console-output veilig in Windows/GitKraken.
    """

    ENGINE_NAME = "Project Phoenix Start Analysis Engine"
    ENGINE_VERSION = "v5.0"

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

        start_log_path = self.project_output_root / "project_start_analysis_log.json"
        start_dashboard_path = self.project_output_root / "project_start_analysis_dashboard.html"

        started_at = datetime.now().isoformat(timespec="seconds")

        steps: Dict[str, Any] = {}

        workflow_step = self.run_step(
            step_key="central_project_analyzer_workflow",
            step_name="Centrale Project Analyzer Workflow draaien",
            runner=lambda: ProjectAnalyzerWorkflow(
                project_output_root=self.project_output_root,
                bib_output_root=self.bib_output_root,
            ).run(),
        )
        steps["central_project_analyzer_workflow"] = workflow_step

        workflow_result = workflow_step.get("output", {})

        launcher_step = self.run_step(
            step_key="project_phoenix_launcher_bridge",
            step_name="Project Phoenix Launcher bijwerken",
            runner=lambda: ProjectAnalyzerLauncherBridge(
                project_output_root=self.project_output_root,
            ).run(
                workflow_result=workflow_result,
            ),
        )
        steps["project_phoenix_launcher_bridge"] = launcher_step

        finished_at = datetime.now().isoformat(timespec="seconds")

        result = {
            "status": self.determine_status(steps),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "purpose": "Een centrale START PROJECTANALYSE-run uitvoeren voor Project Phoenix / BAOEES.",
            "project_output_root": str(self.project_output_root),
            "bib_output_root": str(self.bib_output_root),
            "outputs": {
                "start_log_path": str(start_log_path),
                "start_dashboard_path": str(start_dashboard_path),
                "launcher_path": str(self.project_output_root / "index.html"),
                "workflow_dashboard_path": str(
                    self.project_output_root / "project_analyzer_workflow_dashboard.html"
                ),
                "workflow_log_path": str(
                    self.project_output_root / "project_analyzer_workflow_log.json"
                ),
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
                "Open outputs/projects/project_start_analysis_dashboard.html.",
                "Open outputs/projects/index.html.",
                "Controleer of de launcher de centrale workflow, evidence dashboard en Project ZIP toont.",
                "Gebruik later dit commando als basis voor de START PROJECTANALYSE-knop.",
            ],
            "start_command": "python -m baoees.project_analyzer.project_start_analysis_engine",
        }

        self.write_json(start_log_path, result)
        start_dashboard_path.write_text(
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

    def determine_status(self, steps: Dict[str, Any]) -> str:
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
            warnings.append("Geen kritieke Project Start Analysis-waarschuwingen.")

        return warnings

    def build_html_dashboard(self, result: Dict[str, Any]) -> str:
        outputs = result.get("outputs", {})
        steps = result.get("steps", {})
        warnings = result.get("warnings", [])

        step_cards = ""

        for step in steps.values():
            status = str(step.get("status", ""))
            error_message = step.get("error_message", "")

            details = ""

            output = step.get("output", {})
            if isinstance(output, dict):
                nested_outputs = output.get("outputs", {})
                if isinstance(nested_outputs, dict):
                    for label, path in nested_outputs.items():
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

        for warning in warnings:
            warning_items += f"<li>{self.esc(warning)}</li>"

        launcher_name = Path(outputs.get("launcher_path", "")).name
        start_dashboard_name = Path(outputs.get("start_dashboard_path", "")).name
        workflow_dashboard_name = Path(outputs.get("workflow_dashboard_path", "")).name
        evidence_dashboard_name = Path(outputs.get("project_package_evidence_dashboard", "")).name
        project_zip_name = Path(outputs.get("project_zip", "")).name
        start_log_name = Path(outputs.get("start_log_path", "")).name

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Start Analysis Dashboard</title>
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
    <h1>START PROJECTANALYSE DASHBOARD</h1>
    <p>Project Phoenix / BAOEES centrale run-engine v5.0.</p>
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
        <h3>Startcommando</h3>
        <p><code>{self.esc(result.get("start_command", ""))}</code></p>
      </div>
    </section>

    <h2>Belangrijkste outputs</h2>
    <section class="grid">
      <div class="card">
        <h3>Launcher</h3>
        <p><a href="{self.esc(launcher_name)}">{self.esc(launcher_name)}</a></p>
      </div>
      <div class="card">
        <h3>Start Dashboard</h3>
        <p><a href="{self.esc(start_dashboard_name)}">{self.esc(start_dashboard_name)}</a></p>
      </div>
      <div class="card">
        <h3>Workflow Dashboard</h3>
        <p><a href="{self.esc(workflow_dashboard_name)}">{self.esc(workflow_dashboard_name)}</a></p>
      </div>
      <div class="card">
        <h3>Evidence Dashboard</h3>
        <p><a href="{self.esc(evidence_dashboard_name)}">{self.esc(evidence_dashboard_name)}</a></p>
      </div>
      <div class="card">
        <h3>Project ZIP</h3>
        <p><a href="{self.esc(project_zip_name)}">{self.esc(project_zip_name)}</a></p>
      </div>
      <div class="card">
        <h3>Start Log</h3>
        <p><a href="{self.esc(start_log_name)}">{self.esc(start_log_name)}</a></p>
      </div>
    </section>

    <h2>Run-stappen</h2>
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
            encoding="utf-8-sig",
        )

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)

        if stream is None:
            continue

        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def safe_print_json(data: Dict[str, Any]) -> None:
    try:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    except UnicodeEncodeError:
        print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


def main() -> None:
    configure_console_output()
    engine = ProjectStartAnalysisEngine()
    result = engine.run()
    safe_print_json(result)


if __name__ == "__main__":
    main()