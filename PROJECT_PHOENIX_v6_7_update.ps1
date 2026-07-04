# PROJECT PHOENIX v6.7 UPDATE
# Doel: Error Diagnostics & Auto Repair Engine uit Brewster Wizard kennis overzetten naar Phoenix.
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.7 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$DiagnosticsEnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\project_error_diagnostics_engine.py"
$AutoRepairEnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\project_auto_repair_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_7.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_7.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v6_7_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $DiagnosticsEnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($DiagnosticsEnginePath, $AutoRepairEnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v6_7_$Timestamp" -Force
    }
}

$DiagnosticsEngineContent = @'
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectErrorDiagnosticsEngine:
    ENGINE_NAME = "Project Phoenix Error Diagnostics Engine"
    ENGINE_VERSION = "v6.7"

    def __init__(self) -> None:
        self.project_output_root = PROJECT_ROOT / "outputs" / "projects"
        self.diagnostics_log_path = (
            self.project_output_root
            / "project_error_diagnostics_log.json"
        )
        self.diagnostics_dashboard_path = (
            self.project_output_root
            / "project_error_diagnostics_dashboard.html"
        )
        self.health_log_path = (
            self.project_output_root
            / "project_analysis_health_check_log.json"
        )
        self.runner_paths = [
            PROJECT_ROOT / "START_PROJECTANALYSE.bat",
            PROJECT_ROOT / "START_PROJECTANALYSE.ps1",
        ]

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        health_log = self.read_json(self.health_log_path)
        diagnostics = []
        diagnostics.extend(self.diagnose_health_log(health_log))
        diagnostics.extend(self.diagnose_runner_files())
        diagnostics.extend(self.diagnose_recent_logs())

        severity = self.highest_severity(diagnostics)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "health_log_path": str(self.health_log_path),
            "diagnostics_log_path": str(self.diagnostics_log_path),
            "diagnostics_dashboard_path": str(self.diagnostics_dashboard_path),
            "severity": severity,
            "diagnostic_count": len(diagnostics),
            "safe_repair_count": len(
                [item for item in diagnostics if item.get("safe_repair_available")]
            ),
            "manual_review_count": len(
                [item for item in diagnostics if item.get("manual_review_required")]
            ),
            "diagnostics": diagnostics,
            "next_steps": self.build_next_steps(diagnostics),
        }

        self.write_json(self.diagnostics_log_path, result)
        self.write_text(
            self.diagnostics_dashboard_path,
            self.build_dashboard(result),
        )

        return result

    def diagnose_health_log(
        self,
        health_log: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        diagnostics: List[Dict[str, Any]] = []

        if not health_log:
            diagnostics.append(
                self.item(
                    code="HC-MISSING",
                    title="Health check log ontbreekt",
                    severity="warning",
                    source="project_analysis_health_check_log.json",
                    cause="De health check is nog niet uitgevoerd of het logbestand ontbreekt.",
                    repair="Voer project_analysis_health_check_engine.py opnieuw uit.",
                    safe_repair_available=True,
                    repair_action="run_health_check",
                )
            )
            return diagnostics

        checks = health_log.get("checks", [])

        if not isinstance(checks, list):
            diagnostics.append(
                self.item(
                    code="HC-INVALID",
                    title="Health check log heeft onverwachte structuur",
                    severity="warning",
                    source=str(self.health_log_path),
                    cause="Het JSON-logbestand bevat geen geldige checks-lijst.",
                    repair="Voer de health check opnieuw uit.",
                    safe_repair_available=True,
                    repair_action="run_health_check",
                )
            )
            return diagnostics

        for check in checks:
            if not isinstance(check, dict):
                continue

            if check.get("passed"):
                continue

            relative_path = str(check.get("relative_path", ""))
            category = str(check.get("category", "unknown"))

            diagnostics.append(
                self.item(
                    code="OUTPUT-MISSING",
                    title=f"Output ontbreekt of is leeg: {relative_path}",
                    severity="warning",
                    source=relative_path,
                    cause=check.get("message", "Ontbrekende of lege output."),
                    repair=self.repair_text_for_category(category),
                    safe_repair_available=True,
                    repair_action=self.repair_action_for_category(category),
                    extra={
                        "category": category,
                        "relative_path": relative_path,
                    },
                )
            )

        return diagnostics

    def diagnose_runner_files(self) -> List[Dict[str, Any]]:
        diagnostics: List[Dict[str, Any]] = []

        for runner_path in self.runner_paths:
            if not runner_path.exists():
                diagnostics.append(
                    self.item(
                        code="RUNNER-MISSING",
                        title=f"Runner ontbreekt: {runner_path.name}",
                        severity="error",
                        source=self.safe_relative_path(runner_path),
                        cause="START_PROJECTANALYSE-runner ontbreekt.",
                        repair="Runner opnieuw genereren via v6.7 update.",
                        safe_repair_available=True,
                        repair_action="restore_runner",
                    )
                )
                continue

            text = runner_path.read_text(encoding="utf-8", errors="ignore")

            required_tokens = [
                "brewster_knowledge_migration_engine.py",
                "project_start_analysis_engine.py",
                "project_analysis_health_check_engine.py",
                "project_error_diagnostics_engine.py",
                "project_auto_repair_engine.py",
            ]

            missing_tokens = [
                token for token in required_tokens if token not in text
            ]

            if missing_tokens:
                diagnostics.append(
                    self.item(
                        code="RUNNER-INCOMPLETE",
                        title=f"Runner is onvolledig: {runner_path.name}",
                        severity="warning",
                        source=self.safe_relative_path(runner_path),
                        cause="Niet alle verplichte engines zijn gekoppeld.",
                        repair="Runner opnieuw genereren via v6.7 update.",
                        safe_repair_available=True,
                        repair_action="restore_runner",
                        extra={"missing_tokens": missing_tokens},
                    )
                )

        return diagnostics

    def diagnose_recent_logs(self) -> List[Dict[str, Any]]:
        diagnostics: List[Dict[str, Any]] = []

        log_files = list(self.project_output_root.glob("*log*.json"))

        for path in log_files:
            data = self.read_json(path)

            if not data:
                diagnostics.append(
                    self.item(
                        code="LOG-UNREADABLE",
                        title=f"Logbestand niet leesbaar: {path.name}",
                        severity="warning",
                        source=self.safe_relative_path(path),
                        cause="JSON-log kon niet worden gelezen.",
                        repair="Betreffende engine opnieuw uitvoeren.",
                        safe_repair_available=False,
                        manual_review_required=True,
                    )
                )
                continue

            status = str(data.get("status", "")).upper()

            if status in ["ERROR", "FOUT", "MISLUKT", "ONVOLLEDIG"]:
                diagnostics.append(
                    self.item(
                        code="LOG-STATUS-ISSUE",
                        title=f"Logbestand meldt probleem: {path.name}",
                        severity="warning",
                        source=self.safe_relative_path(path),
                        cause=f"Logstatus is {status}.",
                        repair="Betreffende engine opnieuw uitvoeren of handmatig controleren.",
                        safe_repair_available=False,
                        manual_review_required=True,
                    )
                )

        return diagnostics

    def repair_text_for_category(self, category: str) -> str:
        mapping = {
            "runner": "START_PROJECTANALYSE runners opnieuw genereren.",
            "dashboard": "Launcher bridge en health check opnieuw uitvoeren.",
            "log": "Betreffende engine opnieuw uitvoeren.",
            "package": "Evidence en projectpakket engine opnieuw uitvoeren.",
            "evidence": "Evidence engine opnieuw uitvoeren.",
            "report": "Rapportagepackage en DOCX/PDF-export opnieuw uitvoeren.",
            "bronvermelding": "Evidence engine opnieuw uitvoeren.",
        }

        return mapping.get(category, "Projectanalyse opnieuw uitvoeren.")

    def repair_action_for_category(self, category: str) -> str:
        mapping = {
            "runner": "restore_runner",
            "dashboard": "run_launcher_and_health",
            "log": "run_health_check",
            "package": "run_evidence_package",
            "evidence": "run_evidence_package",
            "report": "run_report_export",
            "bronvermelding": "run_evidence_package",
        }

        return mapping.get(category, "run_health_check")

    def item(
        self,
        code: str,
        title: str,
        severity: str,
        source: str,
        cause: str,
        repair: str,
        safe_repair_available: bool,
        repair_action: str = "",
        manual_review_required: bool = False,
        extra: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "code": code,
            "title": title,
            "severity": severity,
            "source": source,
            "cause": cause,
            "repair": repair,
            "safe_repair_available": safe_repair_available,
            "repair_action": repair_action,
            "manual_review_required": manual_review_required,
            "extra": extra or {},
        }

    def highest_severity(self, diagnostics: List[Dict[str, Any]]) -> str:
        if any(item.get("severity") == "error" for item in diagnostics):
            return "error"

        if any(item.get("severity") == "warning" for item in diagnostics):
            return "warning"

        return "ok"

    def build_next_steps(self, diagnostics: List[Dict[str, Any]]) -> List[str]:
        if not diagnostics:
            return [
                "Geen problemen gevonden.",
                "Auto Repair hoeft niets te herstellen.",
                "Leg v6.7 vast met git add, commit en push.",
            ]

        return [
            "Voer Project Auto Repair Engine uit.",
            "Controleer daarna project_auto_repair_dashboard.html.",
            "Voer START_PROJECTANALYSE opnieuw uit als er herstelacties zijn uitgevoerd.",
        ]

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        rows: List[str] = []

        for item in result.get("diagnostics", []):
            rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('code', ''))}</td>"
                f"<td>{self.esc(item.get('severity', ''))}</td>"
                f"<td>{self.esc(item.get('title', ''))}</td>"
                f"<td><code>{self.esc(item.get('source', ''))}</code></td>"
                f"<td>{self.esc(item.get('cause', ''))}</td>"
                f"<td>{self.esc(item.get('repair', ''))}</td>"
                "</tr>"
            )

        if not rows:
            rows.append(
                "<tr>"
                "<td>OK</td>"
                "<td>ok</td>"
                "<td>Geen fouten gevonden</td>"
                "<td>-</td>"
                "<td>-</td>"
                "<td>Geen herstel nodig</td>"
                "</tr>"
            )

        rows_text = "".join(rows)

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix Error Diagnostics v6.7</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px; }}
    section {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
    h1, h2 {{ color: #f8fafc; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #1e293b; }}
    code {{ color: #bfdbfe; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Project Phoenix Error Diagnostics v6.7</h1>
    <p>Status: <strong>{self.esc(result.get("severity", ""))}</strong></p>
    <p>Foutherkenning op basis van health check, runners en logbestanden.</p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <p>Diagnoses: {self.esc(result.get("diagnostic_count", 0))}</p>
    <p>Veilig herstel beschikbaar: {self.esc(result.get("safe_repair_count", 0))}</p>
    <p>Handmatige controle nodig: {self.esc(result.get("manual_review_count", 0))}</p>
  </section>

  <section>
    <h2>Diagnoses</h2>
    <table>
      <tr>
        <th>Code</th>
        <th>Ernst</th>
        <th>Titel</th>
        <th>Bron</th>
        <th>Oorzaak</th>
        <th>Hersteladvies</th>
      </tr>
      {rows_text}
    </table>
  </section>
</main>
</body>
</html>
"""

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def safe_relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except Exception:
            return str(path)

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


ErrorDiagnosticsEngine = ProjectErrorDiagnosticsEngine
ProjectDiagnosticsEngine = ProjectErrorDiagnosticsEngine


def main() -> None:
    engine = ProjectErrorDiagnosticsEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$AutoRepairEngineContent = @'
from __future__ import annotations

import html
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectAutoRepairEngine:
    ENGINE_NAME = "Project Phoenix Auto Repair Engine"
    ENGINE_VERSION = "v6.7"

    def __init__(self) -> None:
        self.project_output_root = PROJECT_ROOT / "outputs" / "projects"
        self.diagnostics_log_path = (
            self.project_output_root
            / "project_error_diagnostics_log.json"
        )
        self.repair_plan_path = (
            self.project_output_root
            / "project_auto_repair_plan.json"
        )
        self.repair_log_path = (
            self.project_output_root
            / "project_auto_repair_log.json"
        )
        self.repair_dashboard_path = (
            self.project_output_root
            / "project_auto_repair_dashboard.html"
        )

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        diagnostics_log = self.read_json(self.diagnostics_log_path)
        diagnostics = diagnostics_log.get("diagnostics", [])

        if not isinstance(diagnostics, list):
            diagnostics = []

        repair_plan = self.build_repair_plan(diagnostics)
        self.write_json(self.repair_plan_path, repair_plan)

        repair_actions = self.execute_repair_plan(repair_plan)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "diagnostics_log_path": str(self.diagnostics_log_path),
            "repair_plan_path": str(self.repair_plan_path),
            "repair_log_path": str(self.repair_log_path),
            "repair_dashboard_path": str(self.repair_dashboard_path),
            "diagnostic_count": len(diagnostics),
            "planned_action_count": len(repair_plan.get("actions", [])),
            "executed_action_count": len(repair_actions),
            "actions": repair_actions,
            "next_steps": [
                "Controleer project_auto_repair_dashboard.html.",
                "Voer health check opnieuw uit.",
                "Voer diagnostics opnieuw uit.",
                "Leg v6.7 vast als de tree clean gemaakt kan worden.",
            ],
        }

        self.write_json(self.repair_log_path, result)
        self.write_text(
            self.repair_dashboard_path,
            self.build_dashboard(result),
        )

        return result

    def build_repair_plan(
        self,
        diagnostics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        actions: List[Dict[str, Any]] = []

        seen = set()

        for item in diagnostics:
            if not item.get("safe_repair_available"):
                continue

            repair_action = str(item.get("repair_action", ""))

            if not repair_action:
                continue

            if repair_action in seen:
                continue

            seen.add(repair_action)

            actions.append(
                {
                    "repair_action": repair_action,
                    "source_code": item.get("code", ""),
                    "source_title": item.get("title", ""),
                    "safe": True,
                    "status": "GEPLAND",
                }
            )

        if not actions:
            actions.append(
                {
                    "repair_action": "ensure_base_directories",
                    "source_code": "BASE",
                    "source_title": "Basis mappen controleren",
                    "safe": True,
                    "status": "GEPLAND",
                }
            )

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "actions": actions,
        }

    def execute_repair_plan(
        self,
        repair_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        executed: List[Dict[str, Any]] = []

        actions = repair_plan.get("actions", [])

        if not isinstance(actions, list):
            actions = []

        for action in actions:
            repair_action = str(action.get("repair_action", ""))

            if repair_action == "ensure_base_directories":
                executed.append(self.ensure_base_directories())
            elif repair_action == "run_health_check":
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_analysis_health_check_engine.py",
                        repair_action,
                    )
                )
            elif repair_action == "run_report_export":
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_report_bib_engine.py",
                        "run_report_package",
                    )
                )
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_report_export_engine.py",
                        repair_action,
                    )
                )
            elif repair_action == "run_evidence_package":
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_package_evidence_engine.py",
                        repair_action,
                    )
                )
            elif repair_action == "run_launcher_and_health":
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_analyzer_launcher_bridge.py",
                        "run_launcher_bridge",
                    )
                )
                executed.append(
                    self.run_python_engine(
                        "baoees/project_analyzer/project_analysis_health_check_engine.py",
                        repair_action,
                    )
                )
            elif repair_action == "restore_runner":
                executed.append(
                    {
                        "repair_action": repair_action,
                        "status": "OVERGESLAGEN",
                        "message": "Runner-herstel gebeurt via het v6.7 updatebestand en is al toegepast.",
                    }
                )
            else:
                executed.append(
                    {
                        "repair_action": repair_action,
                        "status": "ONBEKEND",
                        "message": "Geen veilige automatische handler beschikbaar.",
                    }
                )

        return executed

    def ensure_base_directories(self) -> Dict[str, Any]:
        paths = [
            PROJECT_ROOT / "outputs",
            PROJECT_ROOT / "outputs" / "projects",
            PROJECT_ROOT / "outputs" / "bib",
            PROJECT_ROOT / "outputs" / "bib" / "knowledge",
            PROJECT_ROOT / "outputs" / "bib" / "index",
            PROJECT_ROOT / "outputs" / "bib" / "dashboards",
            PROJECT_ROOT / "outputs" / "projects" / "Bronvermelding_van_dit_project",
        ]

        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

        return {
            "repair_action": "ensure_base_directories",
            "status": "UITGEVOERD",
            "message": "Basis mappen zijn aanwezig.",
            "paths": [str(path) for path in paths],
        }

    def run_python_engine(
        self,
        relative_script_path: str,
        repair_action: str,
    ) -> Dict[str, Any]:
        script_path = PROJECT_ROOT / relative_script_path

        if not script_path.exists():
            return {
                "repair_action": repair_action,
                "status": "MISLUKT",
                "message": f"Script ontbreekt: {relative_script_path}",
            }

        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
        )

        return {
            "repair_action": repair_action,
            "script": relative_script_path,
            "status": "UITGEVOERD" if completed.returncode == 0 else "MISLUKT",
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        rows: List[str] = []

        for item in result.get("actions", []):
            rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('repair_action', ''))}</td>"
                f"<td>{self.esc(item.get('status', ''))}</td>"
                f"<td>{self.esc(item.get('message', item.get('script', '')))}</td>"
                "</tr>"
            )

        rows_text = "".join(rows)

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix Auto Repair v6.7</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px; }}
    section {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
    h1, h2 {{ color: #f8fafc; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #1e293b; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Project Phoenix Auto Repair v6.7</h1>
    <p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
    <p>Veilige automatische reparaties op basis van diagnostics.</p>
  </section>

  <section>
    <h2>Samenvatting</h2>
    <p>Diagnoses: {self.esc(result.get("diagnostic_count", 0))}</p>
    <p>Geplande acties: {self.esc(result.get("planned_action_count", 0))}</p>
    <p>Uitgevoerde acties: {self.esc(result.get("executed_action_count", 0))}</p>
  </section>

  <section>
    <h2>Reparatie-acties</h2>
    <table>
      <tr>
        <th>Actie</th>
        <th>Status</th>
        <th>Bericht</th>
      </tr>
      {rows_text}
    </table>
  </section>
</main>
</body>
</html>
"""

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


AutoRepairEngine = ProjectAutoRepairEngine
ProjectRepairEngine = ProjectAutoRepairEngine


def main() -> None:
    engine = ProjectAutoRepairEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.7
echo ============================================================
echo.

echo [1/12] Brewster kennis migreren...
python baoees\project_analyzer\brewster_knowledge_migration_engine.py
if errorlevel 1 goto error

echo [2/12] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [3/12] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [4/12] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [5/12] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [6/12] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [7/12] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [8/12] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [9/12] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo [10/12] Error diagnostics uitvoeren...
python baoees\project_analyzer\project_error_diagnostics_engine.py
if errorlevel 1 goto error

echo [11/12] Auto repair uitvoeren...
python baoees\project_analyzer\project_auto_repair_engine.py
if errorlevel 1 goto error

echo [12/12] Health check na reparatie uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.7 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\projects\project_error_diagnostics_dashboard.html" (
    start "" "outputs\projects\project_error_diagnostics_dashboard.html"
)

if exist "outputs\projects\project_auto_repair_dashboard.html" (
    start "" "outputs\projects\project_auto_repair_dashboard.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.7 is gestopt.
echo Controleer de foutmelding hierboven.
echo.
git status
pause
exit /b 1
'@

$Ps1RunnerContent = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.7" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Steps = @(
    @{ Name = "Brewster kennis migreren"; Command = "baoees\project_analyzer\brewster_knowledge_migration_engine.py" },
    @{ Name = "Startanalyse"; Command = "baoees\project_analyzer\project_start_analysis_engine.py" },
    @{ Name = "Workflow"; Command = "baoees\project_analyzer\project_analyzer_workflow_engine.py" },
    @{ Name = "AAIE/BIB aannames"; Command = "baoees\project_analyzer\aaie_bib_assumption_loader.py" },
    @{ Name = "Projectrapportagepackage"; Command = "baoees\project_analyzer\project_report_bib_engine.py" },
    @{ Name = "DOCX/PDF export"; Command = "baoees\project_analyzer\project_report_export_engine.py" },
    @{ Name = "Evidence en projectpakket"; Command = "baoees\project_analyzer\project_package_evidence_engine.py" },
    @{ Name = "Launcher bridge en startdashboard"; Command = "baoees\project_analyzer\project_analyzer_launcher_bridge.py" },
    @{ Name = "Health check"; Command = "baoees\project_analyzer\project_analysis_health_check_engine.py" },
    @{ Name = "Error diagnostics"; Command = "baoees\project_analyzer\project_error_diagnostics_engine.py" },
    @{ Name = "Auto repair"; Command = "baoees\project_analyzer\project_auto_repair_engine.py" },
    @{ Name = "Health check na reparatie"; Command = "baoees\project_analyzer\project_analysis_health_check_engine.py" }
)

$Index = 1

foreach ($Step in $Steps) {
    Write-Host ""
    Write-Host "[$Index/$($Steps.Count)] $($Step.Name) uitvoeren..." -ForegroundColor Yellow
    python $Step.Command
    if ($LASTEXITCODE -ne 0) {
        throw "Stap mislukt: $($Step.Name)"
    }
    $Index++
}

Write-Host ""
Write-Host "PROJECT PHOENIX v6.7 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$DiagnosticsDashboard = Join-Path $PSScriptRoot "outputs\projects\project_error_diagnostics_dashboard.html"
$RepairDashboard = Join-Path $PSScriptRoot "outputs\projects\project_auto_repair_dashboard.html"

if (Test-Path $DiagnosticsDashboard) {
    Start-Process $DiagnosticsDashboard
}

if (Test-Path $RepairDashboard) {
    Start-Process $RepairDashboard
}

git status
'@

Set-Content -Path $DiagnosticsEnginePath -Value $DiagnosticsEngineContent -Encoding UTF8
Set-Content -Path $AutoRepairEnginePath -Value $AutoRepairEngineContent -Encoding UTF8
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1RunnerContent -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1RunnerContent -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Error Diagnostics and Auto Repair Connector"
    engine_version = "v6.7"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    diagnostics_engine = "$DiagnosticsEnginePath"
    auto_repair_engine = "$AutoRepairEnginePath"
    start_projectanalyse_bat = "$BatPath"
    start_projectanalyse_ps1 = "$Ps1Path"
    versioned_bat = "$VersionedBatPath"
    versioned_ps1 = "$VersionedPs1Path"
    purpose = "Voegt foutherkenning en veilige automatische foutreparatie toe aan Phoenix."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven:" -ForegroundColor Green
Write-Host " - baoees\project_analyzer\project_error_diagnostics_engine.py"
Write-Host " - baoees\project_analyzer\project_auto_repair_engine.py"
Write-Host " - START_PROJECTANALYSE.bat"
Write-Host " - START_PROJECTANALYSE.ps1"
Write-Host " - START_PROJECTANALYSE_v6_7.bat"
Write-Host " - START_PROJECTANALYSE_v6_7.ps1"
Write-Host " - outputs\projects\start_projectanalyse_v6_7_update_log.json"

Write-Host ""
Write-Host "Syntaxcontrole diagnostics en auto repair engines..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\project_error_diagnostics_engine.py
python -m py_compile baoees\project_analyzer\project_auto_repair_engine.py

Write-Host ""
Write-Host "Test START_PROJECTANALYSE_v6_7.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v6_7.ps1

Write-Host ""
Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "PROJECT PHOENIX v6.7 UPDATE KLAAR" -ForegroundColor Green
