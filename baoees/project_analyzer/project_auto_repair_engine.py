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
