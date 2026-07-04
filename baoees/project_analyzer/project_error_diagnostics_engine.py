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
