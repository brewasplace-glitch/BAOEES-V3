# PROJECT PHOENIX v7.9 UPDATE
# Phoenix Task Status & Roadmap Update Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.9 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Dit script moet vanuit de root van de PROJECT-PHOENIX repository worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "apps\brewster_engineering_wizard\project_analyzer\phoenix_task_status_roadmap_update_engine.py"
$ScriptDir = Join-Path $ProjectRoot "scripts"
$RunnerPs1 = Join-Path $ScriptDir "START_PROJECTANALYSE_v7_9.ps1"
$RunnerBat = Join-Path $ScriptDir "START_PROJECTANALYSE_v7_9.bat"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_9_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $RunnerPs1, $RunnerBat)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_9_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
import subprocess
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


class PhoenixTaskStatusRoadmapUpdateEngine:
    ENGINE_NAME = "Project Phoenix Task Status & Roadmap Update Engine"
    ENGINE_VERSION = "v7.9"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "roadmap_status"

        self.roadmap_v76_path = self.outputs / "phoenix_task_roadmap_v7_6.json"
        self.selected_task_v77_path = self.outputs / "phoenix_selected_task_v7_7.json"
        self.builder_plan_v78_path = self.outputs / "phoenix_automated_task_builder_plan_v7_8.json"
        self.scaffold_log_v78_path = self.outputs / "phoenix_automated_task_scaffold_log_v7_8.json"

        self.roadmap_status_path = self.outputs / "phoenix_task_roadmap_status_v7_9.json"
        self.progress_path = self.outputs / "phoenix_progress_overview_v7_9.json"
        self.next_go_path = self.outputs / "phoenix_next_go_step_v7_9.json"
        self.changelog_path = self.outputs / "phoenix_task_changelog_v7_9.json"
        self.dashboard_path = self.outputs / "phoenix_roadmap_status_dashboard_v7_9.html"
        self.log_path = self.outputs / "phoenix_task_status_roadmap_update_log_v7_9.json"
        self.doc_path = self.docs / "phoenix_task_status_roadmap_update_v7_9.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        roadmap = self.read_json(self.roadmap_v76_path)
        selected_task = self.read_json(self.selected_task_v77_path)
        builder_plan = self.read_json(self.builder_plan_v78_path)
        scaffold_log = self.read_json(self.scaffold_log_v78_path)
        git_state = self.get_git_state()

        updated_roadmap = self.update_roadmap_status(roadmap, selected_task, builder_plan, scaffold_log, git_state)
        progress = self.build_progress(updated_roadmap, git_state)
        next_go = self.build_next_go(updated_roadmap)
        changelog = self.build_changelog(selected_task, builder_plan, scaffold_log, git_state, progress)

        self.write_json(self.roadmap_status_path, updated_roadmap)
        self.write_json(self.progress_path, progress)
        self.write_json(self.next_go_path, next_go)
        self.write_json(self.changelog_path, changelog)
        self.write_text(self.dashboard_path, self.build_dashboard(progress, next_go, changelog))
        self.write_text(self.doc_path, self.build_documentation(progress, next_go))

        selected_status = self.resolve_selected_task_status(selected_task, builder_plan, scaffold_log, git_state)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "roadmap_status_path": str(self.roadmap_status_path),
            "progress_path": str(self.progress_path),
            "next_go_path": str(self.next_go_path),
            "changelog_path": str(self.changelog_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
            "selected_task_id": selected_task.get("task_id", ""),
            "selected_task_status": selected_status,
            "overall_progress_percent": progress.get("overall_progress_percent", 0),
            "next_safe_step": next_go.get("next_safe_step", {}).get("task_id", ""),
            "git_branch": git_state.get("branch", ""),
            "git_clean": git_state.get("is_clean", False),
        }

        self.write_json(self.log_path, result)
        return result

    def update_roadmap_status(
        self,
        roadmap: Dict[str, Any],
        selected_task: Dict[str, Any],
        builder_plan: Dict[str, Any],
        scaffold_log: Dict[str, Any],
        git_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated = dict(roadmap) if roadmap else {"tasks": []}
        tasks = list(updated.get("tasks", []))
        selected_id = selected_task.get("task_id", "")
        resolved_status = self.resolve_selected_task_status(selected_task, builder_plan, scaffold_log, git_state)

        for task in tasks:
            if not isinstance(task, dict):
                continue
            if task.get("task_id") == selected_id:
                task["status"] = resolved_status
                task["last_status_update"] = datetime.now().isoformat(timespec="seconds")
                task["last_commit"] = git_state.get("latest_commit", "")
                task["last_commit_message"] = git_state.get("latest_commit_message", "")
                task["status_source"] = self.ENGINE_NAME
                task["status_note"] = self.status_note(resolved_status)
                break

        updated["status"] = "ACTIEF_BIJGEWERKT"
        updated["engine_update"] = self.ENGINE_NAME
        updated["engine_update_version"] = self.ENGINE_VERSION
        updated["updated_at"] = datetime.now().isoformat(timespec="seconds")
        updated["tasks"] = tasks
        updated["task_count"] = len(tasks)
        updated["git_state_at_update"] = git_state
        return updated

    def resolve_selected_task_status(
        self,
        selected_task: Dict[str, Any],
        builder_plan: Dict[str, Any],
        scaffold_log: Dict[str, Any],
        git_state: Dict[str, Any],
    ) -> str:
        if not selected_task:
            return "unknown"

        scaffold_results = builder_plan.get("scaffold_results", []) if isinstance(builder_plan, dict) else []
        created_count = len([item for item in scaffold_results if isinstance(item, dict) and item.get("action") == "created"])

        if git_state.get("is_clean") and created_count > 0:
            return "committed"
        if created_count > 0:
            return "scaffolded"
        if scaffold_log.get("results"):
            return "scaffold_checked"
        return selected_task.get("status", "open")

    def status_note(self, status: str) -> str:
        notes = {
            "committed": "Scaffold is aangemaakt en working tree was clean bij statusupdate; vermoedelijk gecommit/gepusht.",
            "scaffolded": "Scaffoldbestanden zijn aangemaakt maar working tree is nog niet clean.",
            "scaffold_checked": "Scaffoldlog gevonden; controle nodig.",
            "open": "Taak staat nog open.",
            "unknown": "Geen taakstatus bepaald.",
        }
        return notes.get(status, "Status automatisch bepaald door v7.9.")

    def build_progress(self, roadmap: Dict[str, Any], git_state: Dict[str, Any]) -> Dict[str, Any]:
        tasks = [task for task in roadmap.get("tasks", []) if isinstance(task, dict)]
        active_statuses = {"done", "committed", "tested", "scaffolded", "gedeeltelijk_of_afgerond"}
        complete_statuses = {"done", "committed"}

        active = [task for task in tasks if task.get("status") in active_statuses]
        complete = [task for task in tasks if task.get("status") in complete_statuses]
        open_tasks = [task for task in tasks if task.get("status", "open") == "open"]

        tracks_seen: List[str] = []
        for task in tasks:
            track_id = task.get("track_id", "")
            if track_id and track_id not in tracks_seen:
                tracks_seen.append(track_id)

        by_track: List[Dict[str, Any]] = []
        for track_id in tracks_seen:
            track_tasks = [task for task in tasks if task.get("track_id") == track_id]
            track_active = [task for task in track_tasks if task.get("status") in active_statuses]
            track_complete = [task for task in track_tasks if task.get("status") in complete_statuses]
            track_name = track_tasks[0].get("track", track_id) if track_tasks else track_id
            by_track.append(
                {
                    "track_id": track_id,
                    "track": track_name,
                    "total_tasks": len(track_tasks),
                    "active_or_partial": len(track_active),
                    "complete": len(track_complete),
                    "open": len(track_tasks) - len(track_active),
                    "progress_percent": round((len(track_active) / len(track_tasks)) * 100, 1) if track_tasks else 0,
                }
            )

        return {
            "status": "ACTIEF_BIJGEWERKT",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_tasks": len(tasks),
            "active_or_partial": len(active),
            "complete_tasks": len(complete),
            "open_tasks": len(open_tasks),
            "overall_progress_percent": round((len(active) / len(tasks)) * 100, 1) if tasks else 0,
            "complete_progress_percent": round((len(complete) / len(tasks)) * 100, 1) if tasks else 0,
            "current_phase": "Roadmap-status, voortgang en volgende GO-stap automatisch bijwerken",
            "last_completed_version": "v7.8 Automated Task Builder",
            "git_state": git_state,
            "by_track": by_track,
        }

    def build_next_go(self, roadmap: Dict[str, Any]) -> Dict[str, Any]:
        tasks = [task for task in roadmap.get("tasks", []) if isinstance(task, dict)]
        open_tasks = [task for task in tasks if task.get("status", "open") == "open"]

        if open_tasks:
            next_task = sorted(open_tasks, key=lambda item: item.get("priority", 999999))[0]
        else:
            next_task = {
                "task_id": "ROADMAP-COMPLETE",
                "title": "Alle roadmaptaken zijn afgehandeld",
                "risk_level": "laag",
                "requires_go": True,
            }

        return {
            "status": "ACTIEF",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "next_safe_step": next_task,
            "recommended_next_version": "v8.0",
            "recommended_next_engine": "Phoenix Task Autopilot Engine",
            "instruction": "Vraag gebruiker om GO voordat de volgende taak inhoudelijk wordt uitgevoerd.",
            "reason": "Na v7.9 kan Phoenix taakstatus bijhouden; volgende stap is gecontroleerde uitvoering van open taken.",
        }

    def build_changelog(
        self,
        selected_task: Dict[str, Any],
        builder_plan: Dict[str, Any],
        scaffold_log: Dict[str, Any],
        git_state: Dict[str, Any],
        progress: Dict[str, Any],
    ) -> Dict[str, Any]:
        event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "roadmap_status_update",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "selected_task_id": selected_task.get("task_id", ""),
            "selected_task_title": selected_task.get("title", ""),
            "resolved_status": self.resolve_selected_task_status(selected_task, builder_plan, scaffold_log, git_state),
            "latest_commit": git_state.get("latest_commit", ""),
            "latest_commit_message": git_state.get("latest_commit_message", ""),
            "overall_progress_percent": progress.get("overall_progress_percent", 0),
        }

        previous = self.read_json(self.changelog_path)
        events = previous.get("events", []) if isinstance(previous, dict) else []
        if not isinstance(events, list):
            events = []
        events.append(event)

        return {
            "status": "ACTIEF",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "events": events,
            "latest_event": event,
        }

    def get_git_state(self) -> Dict[str, Any]:
        status = self.run_git(["status", "--porcelain"])
        branch = self.run_git(["branch", "--show-current"]).strip()
        latest_commit = self.run_git(["rev-parse", "--short", "HEAD"]).strip()
        latest_message = self.run_git(["log", "-1", "--pretty=%s"]).strip()

        return {
            "branch": branch,
            "is_clean": status.strip() == "",
            "porcelain_status": status,
            "latest_commit": latest_commit,
            "latest_commit_message": latest_message,
        }

    def run_git(self, args: List[str]) -> str:
        try:
            completed = subprocess.run(
                ["git"] + args,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            return (completed.stdout or completed.stderr or "").strip()
        except Exception as exc:
            return f"git_error: {exc}"

    def build_dashboard(
        self,
        progress: Dict[str, Any],
        next_go: Dict[str, Any],
        changelog: Dict[str, Any],
    ) -> str:
        next_task = next_go.get("next_safe_step", {})
        track_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('track_id', ''))}</td>"
            f"<td>{self.esc(item.get('track', ''))}</td>"
            f"<td>{self.esc(item.get('active_or_partial', ''))}/{self.esc(item.get('total_tasks', ''))}</td>"
            f"<td>{self.esc(item.get('complete', ''))}</td>"
            f"<td>{self.esc(item.get('progress_percent', ''))}%</td>"
            "</tr>"
            for item in progress.get("by_track", [])
        )

        recent_events = changelog.get("events", [])[-10:]
        event_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('timestamp', ''))}</td>"
            f"<td>{self.esc(item.get('selected_task_id', ''))}</td>"
            f"<td>{self.esc(item.get('resolved_status', ''))}</td>"
            f"<td>{self.esc(item.get('latest_commit_message', ''))}</td>"
            "</tr>"
            for item in recent_events
        )

        git_state = progress.get("git_state", {})

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Roadmap Status v7.9</title>
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
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Task Status & Roadmap Update v7.9</h1>
<p>Status: <strong>{self.esc(progress.get("status", ""))}</strong></p>
<p class="badge">Roadmap voortgang: {self.esc(progress.get("overall_progress_percent", 0))}%</p>
<p>Volledig afgerond/gecommit: {self.esc(progress.get("complete_progress_percent", 0))}%</p>
</section>

<section>
<h2>Git-status bij update</h2>
<p>Branch: <code>{self.esc(git_state.get("branch", ""))}</code></p>
<p>Clean: <strong>{self.esc(git_state.get("is_clean", ""))}</strong></p>
<p>Laatste commit: <code>{self.esc(git_state.get("latest_commit", ""))}</code> — {self.esc(git_state.get("latest_commit_message", ""))}</p>
</section>

<section>
<h2>Volgende veilige GO-stap</h2>
<p><strong>{self.esc(next_task.get("task_id", ""))}</strong> — {self.esc(next_task.get("title", ""))}</p>
<p>Risico: <strong>{self.esc(next_task.get("risk_level", ""))}</strong></p>
<p>GO nodig: <strong>{self.esc(next_task.get("requires_go", ""))}</strong></p>
</section>

<section>
<h2>Voortgang per spoor</h2>
<table>
<tr><th>Spoor</th><th>Naam</th><th>Actief/deels</th><th>Complete</th><th>Voortgang</th></tr>
{track_rows}
</table>
</section>

<section>
<h2>Recente changelog-events</h2>
<table>
<tr><th>Tijd</th><th>Taak</th><th>Status</th><th>Commit</th></tr>
{event_rows}
</table>
</section>
</main>
</body>
</html>
"""

    def build_documentation(self, progress: Dict[str, Any], next_go: Dict[str, Any]) -> str:
        next_task = next_go.get("next_safe_step", {})
        lines = [
            "# Project Phoenix Task Status & Roadmap Update v7.9",
            "",
            "Deze engine werkt na elke taak de roadmapstatus, voortgang, changelog en volgende GO-stap bij.",
            "",
            f"- Totale taken: {progress.get('total_tasks', 0)}",
            f"- Actief/deels afgerond: {progress.get('active_or_partial', 0)}",
            f"- Volledig/gecommit: {progress.get('complete_tasks', 0)}",
            f"- Voortgang: {progress.get('overall_progress_percent', 0)}%",
            "",
            "## Volgende veilige stap",
            "",
            f"- Taak: {next_task.get('task_id', '')}",
            f"- Titel: {next_task.get('title', '')}",
            f"- Risico: {next_task.get('risk_level', '')}",
            "",
        ]
        return "\n".join(lines)

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


RoadmapStatusEngine = PhoenixTaskStatusRoadmapUpdateEngine
PhoenixRoadmapUpdateEngine = PhoenixTaskStatusRoadmapUpdateEngine


def main() -> None:
    engine = PhoenixTaskStatusRoadmapUpdateEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$RunnerPs1Content = @'
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - TASK STATUS / ROADMAP UPDATE v7.9" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_status_roadmap_update_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Task Status Roadmap Update Engine v7.9 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_roadmap_status_dashboard_v7_9.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

$RunnerBatContent = @'
@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - TASK STATUS / ROADMAP UPDATE v7.9

python apps\brewster_engineering_wizard\project_analyzer\phoenix_task_status_roadmap_update_engine.py || goto error

if exist "outputs\projects\phoenix_roadmap_status_dashboard_v7_9.html" (
    start "" "outputs\projects\phoenix_roadmap_status_dashboard_v7_9.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Task Status Roadmap Update Engine v7.9 is gestopt.
git status
pause
exit /b 1
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $RunnerPs1 -Value $RunnerPs1Content -Encoding UTF8
Set-Content -Path $RunnerBat -Value $RunnerBatContent -Encoding ASCII

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Task Status Roadmap Update Connector"
    engine_version = "v7.9"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    engine_path = "$EnginePath"
    runner_ps1 = "$RunnerPs1"
    runner_bat = "$RunnerBat"
    repository_policy = "Alleen PROJECT-PHOENIX repository"
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole Phoenix Task Status Roadmap Update Engine..." -ForegroundColor Cyan
python -m py_compile .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_status_roadmap_update_engine.py

Write-Host "Run v7.9..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\scripts\START_PROJECTANALYSE_v7_9.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.9 UPDATE KLAAR" -ForegroundColor Green
