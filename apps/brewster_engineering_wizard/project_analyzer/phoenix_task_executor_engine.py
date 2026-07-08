from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parents[3]


PROJECT_ROOT = find_project_root()


class PhoenixTaskExecutorEngine:
    ENGINE_NAME = "Project Phoenix Task Executor / Build Script Factory"
    ENGINE_VERSION = "v7.7"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "task_executor"
        self.generated_scripts = self.outputs / "generated_task_scripts"

        self.roadmap_path = self.outputs / "phoenix_task_roadmap_v7_6.json"
        self.rules_path = self.outputs / "phoenix_build_rules_v7_6.json"
        self.progress_path = self.outputs / "phoenix_progress_overview_v7_6.json"
        self.next_go_path = self.outputs / "phoenix_next_go_step_v7_6.json"

        self.executor_plan_path = self.outputs / "phoenix_task_executor_plan_v7_7.json"
        self.generated_package_path = self.outputs / "phoenix_generated_task_package_v7_7.json"
        self.selected_task_path = self.outputs / "phoenix_selected_task_v7_7.json"
        self.dashboard_path = self.outputs / "phoenix_task_executor_dashboard_v7_7.html"
        self.log_path = self.outputs / "phoenix_task_executor_log_v7_7.json"
        self.doc_path = self.docs / "phoenix_task_executor_v7_7.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)
        self.generated_scripts.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        roadmap = self.read_json(self.roadmap_path)
        rules = self.read_json(self.rules_path)
        progress = self.read_json(self.progress_path)
        next_go = self.read_json(self.next_go_path)

        selected_task = self.select_task(roadmap, next_go)
        task_package = self.build_task_package(selected_task)
        generated_script_path = self.write_task_script(task_package)

        plan = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "selected_task": selected_task,
            "roadmap_path": str(self.roadmap_path),
            "rules_path": str(self.rules_path),
            "progress_path": str(self.progress_path),
            "next_go_path": str(self.next_go_path),
            "generated_task_package_path": str(self.generated_package_path),
            "generated_script_path": str(generated_script_path),
            "roadmap_task_count": roadmap.get("task_count", len(roadmap.get("tasks", []))) if roadmap else 0,
            "overall_progress_percent": progress.get("overall_progress_percent", 0) if progress else 0,
            "go_gate": task_package["go_gate"],
            "execution_mode": {
                "factory_created_script": True,
                "factory_executes_task_now": False,
                "user_go_required_before_task_execution": task_package["go_gate"]["go_required"],
                "auto_commit": False,
                "auto_push": False,
            },
            "next_steps": [
                "Controleer phoenix_task_executor_dashboard_v7_7.html.",
                "Controleer gegenereerd taakscript in outputs/projects/generated_task_scripts.",
                "Geef GO als deze taak uitgevoerd mag worden.",
                "Na GO kan de volgende versie de echte taak uitvoeren of het taakscript verder invullen.",
            ],
        }

        self.write_json(self.executor_plan_path, plan)
        self.write_json(self.generated_package_path, task_package)
        self.write_json(self.selected_task_path, selected_task)
        self.write_text(self.dashboard_path, self.build_dashboard(plan, task_package))
        self.write_text(self.doc_path, self.build_documentation(plan, task_package))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "roadmap_status": "GELEZEN" if roadmap else "ONTBREEKT",
            "rules_status": "GELEZEN" if rules else "ONTBREEKT",
            "selected_task_id": selected_task.get("task_id", ""),
            "selected_task_title": selected_task.get("title", ""),
            "executor_plan_path": str(self.executor_plan_path),
            "generated_package_path": str(self.generated_package_path),
            "selected_task_path": str(self.selected_task_path),
            "generated_script_path": str(generated_script_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
            "go_required": task_package["go_gate"]["go_required"],
            "script_status": task_package["script_status"],
            "next_instruction": "Controleer dashboard en vraag/geef GO voordat het gegenereerde taakscript wordt uitgevoerd.",
        }

        self.write_json(self.log_path, result)
        return result

    def select_task(self, roadmap: Dict[str, Any], next_go: Dict[str, Any]) -> Dict[str, Any]:
        next_task = next_go.get("next_safe_step", {}) if isinstance(next_go, dict) else {}
        if isinstance(next_task, dict) and next_task.get("task_id"):
            return next_task

        tasks = roadmap.get("tasks", []) if isinstance(roadmap, dict) else []
        open_tasks = [
            task for task in tasks
            if isinstance(task, dict) and task.get("status", "open") == "open"
        ]

        if open_tasks:
            return sorted(open_tasks, key=lambda item: item.get("priority", 999999))[0]

        return {
            "task_id": "MANUAL-001",
            "track": "Handmatige vervolgtaak",
            "track_id": "MANUAL",
            "priority": 999999,
            "title": "Manual next task",
            "objective": "Geen open roadmaptaak gevonden; kies handmatig een vervolgstap.",
            "files_to_create_or_modify": [],
            "update_script": "PROJECT_PHOENIX_manual_next_task_update.ps1",
            "test_command": "git status",
            "commit_message": "chore: manual next task",
            "risk_level": "middel",
            "dependencies": [],
            "requires_go": True,
            "expected_result": "Handmatige vervolgstap bepaald.",
            "status": "open",
        }

    def build_task_package(self, task: Dict[str, Any]) -> Dict[str, Any]:
        script_name = self.safe_script_name(task)
        generated_script_path = self.generated_scripts / script_name

        files = task.get("files_to_create_or_modify", [])
        if not isinstance(files, list):
            files = []

        go_required = bool(task.get("requires_go", True))
        risk = str(task.get("risk_level", "middel"))

        return {
            "status": "DRAFT_GO_REQUIRED" if go_required else "DRAFT_READY",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "script_status": "DRAFT_ONLY_NOT_EXECUTED",
            "selected_task": task,
            "generated_script": {
                "name": script_name,
                "path": str(generated_script_path),
                "type": "PowerShell",
                "execution_policy": "Alleen uitvoeren na expliciete GO.",
            },
            "go_gate": {
                "go_required": go_required,
                "risk_level": risk,
                "reason": self.go_reason(task),
                "allowed_next_user_signal": "go",
            },
            "planned_files": files,
            "planned_test_command": task.get("test_command", "git status"),
            "planned_commit_message": task.get("commit_message", "chore: generated task"),
            "planned_workflow": [
                "backup bestaande bestanden",
                "maak of wijzig taakbestanden",
                "run testcommando",
                "toon git status",
                "wacht op review",
                "commit en push pas na goedkeuring",
            ],
            "safety_policy": {
                "no_auto_commit": True,
                "no_auto_push": True,
                "no_delete_without_explicit_rule": True,
                "write_backups": True,
                "show_git_status": True,
            },
        }

    def write_task_script(self, task_package: Dict[str, Any]) -> Path:
        path = Path(task_package["generated_script"]["path"])
        task = task_package["selected_task"]
        files = task_package["planned_files"]

        file_lines = []
        for item in files:
            file_lines.append("# - " + str(item))
        files_comment = "\n".join(file_lines) if file_lines else "# - geen bestanden opgegeven"

        task_id = self.ps_escape(task.get("task_id", ""))
        title = self.ps_escape(task.get("title", ""))
        track = self.ps_escape(task.get("track", ""))
        risk = self.ps_escape(task.get("risk_level", ""))
        test_command = self.ps_escape(task_package.get("planned_test_command", "git status"))
        execution_log_name = self.safe_slug(task.get("task_id", "task")) + "_execution_log.json"

        script = f"""# PROJECT PHOENIX GENERATED TASK SCRIPT
# Gegenereerd door v7.7 Task Executor / Build Script Factory
# Status: DRAFT_ONLY_NOT_EXECUTED
#
# Taak: {task_id} - {title}
# Spoor: {track}
# Risico: {risk}
#
# BELANGRIJK:
# Dit script is een voorbereid taakscript.
# Uitvoeren pas na expliciete GO.
# Geen automatische commit of push.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX GENERATED TASK START" -ForegroundColor Cyan
Write-Host "Taak: {task_id} - {title}" -ForegroundColor Yellow

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {{
    throw "Dit script moet vanuit de root van PROJECT-PHOENIX worden uitgevoerd."
}}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Geplande bestanden:
{files_comment}

# Deze v7.7 factory maakt bewust nog geen inhoudelijke modulewijziging.
# De volgende stap is dat Phoenix per taak echte code/documentatie vult op basis van dit scaffold.

$TaskLogPath = Join-Path $ProjectRoot "outputs\\projects\\generated_task_scripts\\{execution_log_name}"
New-Item -ItemType Directory -Path (Split-Path $TaskLogPath) -Force | Out-Null

$TaskLog = [ordered]@{{
    status = "DRAFT_EXECUTED_NO_CODE_CHANGE"
    task_id = "{task_id}"
    title = "{title}"
    track = "{track}"
    risk_level = "{risk}"
    generated_at = (Get-Date).ToString("s")
    note = "Task scaffold uitgevoerd; inhoudelijke bouw vraagt aparte GO-stap."
}}

$TaskLog | ConvertTo-Json -Depth 5 | Set-Content -Path $TaskLogPath -Encoding UTF8

Write-Host "Gepland testcommando:" -ForegroundColor Cyan
Write-Host "{test_command}" -ForegroundColor Yellow

Write-Host "Git status:" -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX GENERATED TASK KLAAR" -ForegroundColor Green
"""
        self.write_text(path, script)
        return path

    def build_dashboard(self, plan: Dict[str, Any], package: Dict[str, Any]) -> str:
        task = plan["selected_task"]

        files = "".join(
            f"<tr><td><code>{self.esc(item)}</code></td></tr>"
            for item in package.get("planned_files", [])
        ) or "<tr><td>Geen geplande bestanden opgegeven.</td></tr>"

        workflow = "".join(
            f"<li>{self.esc(item)}</li>"
            for item in package.get("planned_workflow", [])
        )

        go = package["go_gate"]

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Task Executor v7.7</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1280px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
.badge {{ display:inline-block; padding:6px 10px; background:#1e293b; border-radius:999px; }}
.warning {{ color:#fde68a; }}
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Task Executor / Build Script Factory v7.7</h1>
<p>Status: <strong>{self.esc(plan.get("status", ""))}</strong></p>
<p>Roadmaptaak geselecteerd en taakscript voorbereid. Het script wordt niet automatisch uitgevoerd.</p>
</section>

<section>
<h2>Geselecteerde taak</h2>
<p><strong>{self.esc(task.get("task_id", ""))}</strong> — {self.esc(task.get("title", ""))}</p>
<p>{self.esc(task.get("objective", ""))}</p>
<p>Spoor: {self.esc(task.get("track", ""))}</p>
<p>Risico: <span class="badge">{self.esc(task.get("risk_level", ""))}</span></p>
<p>Commit: <code>{self.esc(task.get("commit_message", ""))}</code></p>
</section>

<section>
<h2>GO-gate</h2>
<p class="warning">GO vereist: <strong>{self.esc(go.get("go_required", ""))}</strong></p>
<p>Reden: {self.esc(go.get("reason", ""))}</p>
<p>Volgend signaal: <code>{self.esc(go.get("allowed_next_user_signal", "go"))}</code></p>
</section>

<section>
<h2>Voorbereid taakscript</h2>
<p><code>{self.esc(plan.get("generated_script_path", ""))}</code></p>
<p>Status: <strong>{self.esc(package.get("script_status", ""))}</strong></p>
</section>

<section>
<h2>Geplande bestanden</h2>
<table>{files}</table>
</section>

<section>
<h2>Geplande workflow</h2>
<ul>{workflow}</ul>
</section>
</main>
</body>
</html>
"""

    def build_documentation(self, plan: Dict[str, Any], package: Dict[str, Any]) -> str:
        task = plan["selected_task"]
        lines = [
            "# Project Phoenix Task Executor v7.7",
            "",
            "Deze engine zet de Phoenix roadmap om naar uitvoerbare, gecontroleerde taakpakketten.",
            "",
            "## Geselecteerde taak",
            "",
            f"- Taak: {task.get('task_id', '')}",
            f"- Titel: {task.get('title', '')}",
            f"- Spoor: {task.get('track', '')}",
            f"- Risico: {task.get('risk_level', '')}",
            f"- GO vereist: {package['go_gate']['go_required']}",
            "",
            "## Gegenereerd taakscript",
            "",
            f"`{plan.get('generated_script_path', '')}`",
            "",
            "## Werkregel",
            "",
            "Het taakscript wordt alleen voorbereid. Uitvoering, commit en push gebeuren pas na GO en controle.",
            "",
        ]
        return "\n".join(lines)

    def go_reason(self, task: Dict[str, Any]) -> str:
        if task.get("requires_go"):
            return "Roadmaptaak markeert GO als verplicht."
        if task.get("risk_level") in ["hoog", "middel"]:
            return "Risico is niet laag; extra bevestiging gewenst."
        return "Laag risico, maar v7.7 houdt alsnog review vóór uitvoering aan."

    def safe_script_name(self, task: Dict[str, Any]) -> str:
        task_id = self.safe_slug(task.get("task_id", "task"))
        title = self.safe_slug(task.get("title", "task"))
        return f"PROJECT_PHOENIX_{task_id}_{title}_update.ps1"

    def safe_slug(self, value: Any) -> str:
        text = str(value).strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "task"

    def ps_escape(self, value: Any) -> str:
        return str(value).replace('"', '`"').replace("$", "`$")

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
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


TaskExecutorEngine = PhoenixTaskExecutorEngine
PhoenixBuildScriptFactory = PhoenixTaskExecutorEngine


def main() -> None:
    engine = PhoenixTaskExecutorEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
