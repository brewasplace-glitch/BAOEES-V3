# PROJECT PHOENIX v7.6 UPDATE
# Phoenix Build Governance & Task Roadmap Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.6 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Dit script moet vanuit de root van de PROJECT-PHOENIX repository worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "apps\brewster_engineering_wizard\project_analyzer\phoenix_build_governance_engine.py"
$ScriptDir = Join-Path $ProjectRoot "scripts"
$RunnerPs1 = Join-Path $ScriptDir "START_PROJECTANALYSE_v7_6.ps1"
$RunnerBat = Join-Path $ScriptDir "START_PROJECTANALYSE_v7_6.bat"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_6_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $RunnerPs1, $RunnerBat)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_6_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
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


class PhoenixBuildGovernanceEngine:
    ENGINE_NAME = "Project Phoenix Build Governance & Task Roadmap Engine"
    ENGINE_VERSION = "v7.6"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "governance"
        self.context_path = self.outputs / "project_context_v7_1.json"
        self.cad_plan_path = self.outputs / "project_cad_export_plan_v7_5.json"

        self.rules_path = self.outputs / "phoenix_build_rules_v7_6.json"
        self.roadmap_path = self.outputs / "phoenix_task_roadmap_v7_6.json"
        self.progress_path = self.outputs / "phoenix_progress_overview_v7_6.json"
        self.next_go_path = self.outputs / "phoenix_next_go_step_v7_6.json"
        self.dashboard_path = self.outputs / "phoenix_daily_start_dashboard_v7_6.html"
        self.log_path = self.outputs / "phoenix_build_governance_log_v7_6.json"
        self.doc_path = self.docs / "phoenix_build_governance_v7_6.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        rules = self.build_rules()
        roadmap = self.build_roadmap(rules)
        progress = self.build_progress(roadmap)
        next_go = self.build_next_go(roadmap, progress)

        self.write_json(self.rules_path, rules)
        self.write_json(self.roadmap_path, roadmap)
        self.write_json(self.progress_path, progress)
        self.write_json(self.next_go_path, next_go)
        self.write_text(self.dashboard_path, self.build_dashboard(rules, roadmap, progress, next_go))
        self.write_text(self.doc_path, self.build_documentation(rules, roadmap, progress, next_go))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "rules_path": str(self.rules_path),
            "roadmap_path": str(self.roadmap_path),
            "progress_path": str(self.progress_path),
            "next_go_path": str(self.next_go_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
            "task_count": len(roadmap["tasks"]),
            "track_count": len(roadmap["tracks"]),
            "next_safe_step": next_go["next_safe_step"]["task_id"],
            "next_safe_title": next_go["next_safe_step"]["title"],
            "workflow_policy": rules["workflow_policy"],
        }

        self.write_json(self.log_path, result)
        return result

    def build_rules(self) -> Dict[str, Any]:
        return {
            "status": "ACTIEF",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "repository_policy": {
                "main_repository": "PROJECT-PHOENIX",
                "main_branch": "project-phoenix",
                "old_repository_policy": "BREWSTER-ENGINEERING-WIZARD is niet meer het hoofdspoor; BAOEES/Wizard wordt engine-laag binnen Phoenix.",
                "engine_layer_path": "apps/brewster_engineering_wizard/",
                "scripts_path": "scripts/",
                "documentation_path": "DOCS/project_phoenix/",
                "outputs_path": "outputs/projects/",
            },
            "workflow_policy": {
                "no_major_step_without_user_go": True,
                "preferred_delivery": "downloadbare PowerShell update/patch scripts",
                "avoid_manual_python_paste": True,
                "one_task_one_script_one_test_one_commit": True,
                "always_test_before_commit": True,
                "always_end_with_git_status": True,
                "target_end_state": "nothing to commit, working tree clean",
                "backup_before_replace": True,
                "rollback_or_restore_guidance_required": True,
            },
            "task_format": [
                "task_id",
                "track",
                "priority",
                "title",
                "objective",
                "files_to_create_or_modify",
                "update_script",
                "test_command",
                "commit_message",
                "risk_level",
                "dependencies",
                "requires_go",
                "expected_result",
            ],
            "go_rules": {
                "requires_go_for": [
                    "core architecture changes",
                    "runner changes",
                    "database schema changes",
                    "knowledge graph schema changes",
                    "engine orchestration changes",
                    "file moves/deletes",
                    "large generated output changes",
                ],
                "safe_without_extra_go_after_start": [
                    "generate planned update script",
                    "write documentation",
                    "write isolated new engine file",
                    "create dashboards/roadmap JSON",
                ],
            },
            "daily_start_policy": {
                "show_priorities": True,
                "show_progress": True,
                "show_current_phase": True,
                "show_risks": True,
                "show_open_decisions": True,
                "show_last_completed_version": True,
                "show_next_safe_go_step": True,
                "show_git_control": True,
            },
        }

    def build_roadmap(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        tracks = self.build_tracks()
        tasks: List[Dict[str, Any]] = []

        for track in tracks:
            for index in range(1, 21):
                tasks.append(self.build_task(track, index))

        return {
            "status": "ACTIEF",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "roadmap_name": "Project Phoenix Master Build Roadmap",
            "tracks": tracks,
            "tasks": tasks,
            "task_count": len(tasks),
            "planning_policy": {
                "granularity": "honderden kleine gecontroleerde bouwtaken",
                "execution_style": "stap voor stap met update script, test, commit, push, clean tree",
                "go_policy": rules["go_rules"],
            },
        }

    def build_tracks(self) -> List[Dict[str, Any]]:
        return [
            {"id": "S01", "name": "Stabilisatie & automatisering", "priority": 1},
            {"id": "S02", "name": "Hoofdscherm / GUI / dashboards", "priority": 2},
            {"id": "S03", "name": "Project Intake + aannames + projectcontext", "priority": 3},
            {"id": "S04", "name": "Digital Twin + Knowledge Graph", "priority": 4},
            {"id": "S05", "name": "Geotechniek + fundering + constructie", "priority": 5},
            {"id": "S06", "name": "Infra: wegen, parkeren, riolering, waterbouw", "priority": 6},
            {"id": "S07", "name": "Vergunningen: BOPA, Omgevingsvergunning, AERIUS", "priority": 7},
            {"id": "S08", "name": "Kosten, planning, aanbesteding", "priority": 8},
            {"id": "S09", "name": "Rapporten, tekeningen, CAD/BIM/export", "priority": 9},
            {"id": "S10", "name": "Installatie, updates, documentatie, handleidingen", "priority": 10},
        ]

    def build_task(self, track: Dict[str, Any], index: int) -> Dict[str, Any]:
        task_id = f"{track['id']}-{index:03d}"
        slug = track["name"].lower()
        priority = track["priority"] * 100 + index

        title_templates = {
            "S01": [
                "Repo health baseline", "Automated cleanup helper", "Runner validation", "Patch factory",
                "Rollback registry", "Version manifest", "Build progress tracker", "Error diagnostics",
                "Auto repair workflow", "Release checklist", "Branch policy", "Output hygiene",
                "Evidence connector", "Git status gate", "Smoke test suite", "Dependency scanner",
                "Config validator", "Task orchestrator", "Safe delete guard", "Governance dashboard",
            ],
            "S02": [
                "Phoenix start dashboard", "Dagstart dashboard", "Module tiles", "Project selector",
                "Output viewer", "Evidence viewer", "Risk dashboard", "GO gate screen",
                "Engine status panel", "Progress chart", "Settings screen", "Theme/layout baseline",
                "Project cards", "Search interface", "Upload panel", "Wizard mode screen",
                "Autonomous mode screen", "Report preview", "Drawing preview", "Dashboard export",
            ],
            "S03": [
                "Project intake schema", "Natural language intake", "Upload intake", "Location intake",
                "Project type classifier", "Output selector", "AAIE missing data map", "Assumption log",
                "Project context builder", "Context validator", "Source register link", "Variant selector",
                "Project profile templates", "Client data model", "Scope definition", "Risk intake",
                "Decision log", "Project folder maker", "Context dashboard", "Context export",
            ],
            "S04": [
                "Digital Twin schema", "Knowledge Graph schema", "Entity registry", "Relationship registry",
                "Project facts store", "Geometry facts", "Permit facts", "Cost facts",
                "Source trace links", "Assumption graph", "Versioned twin snapshots", "Twin diff engine",
                "Twin consistency checks", "Graph import", "Graph export", "Semantic search hooks",
                "BIM entity mapping", "CAD entity mapping", "Project memory bridge", "Twin dashboard",
            ],
            "S05": [
                "Geotechniek engine", "Groundwater module", "Soil profile module", "Foundation engine",
                "Strip foundation module", "Pile variant module", "Settlement check stub", "Structural engine",
                "Load assumptions", "Load paths", "Column model", "Beam model",
                "Wall model", "Roof model", "OpenSees connector", "CalculiX connector",
                "FreeCAD structural bridge", "Calculation report", "QA/QC checks", "Structural dashboard",
            ],
            "S06": [
                "Road geometry module", "Parking inventory", "Parking balance", "CROW ruleset",
                "Parking regime advice", "Traffic generation", "Mobility paragraph", "Sewer HWA module",
                "Sewer DWA module", "Infiltration storage", "Drainage layout", "Water balance",
                "Hydraulic assumptions", "Civil quantities", "Civil cost link", "Road markings",
                "Lighting/street furniture", "Waterbouw starter", "Infra dashboard", "Infra report",
            ],
            "S07": [
                "Permit intake", "BOPA structure", "Omgevingsvergunning checklist", "AERIUS workflow",
                "Omgevingswet sources", "Rules-on-map source register", "Spatial justification",
                "ETFAL/BOPA paragraph", "Participation plan", "Parking permit paragraph",
                "Traffic permit paragraph", "Water paragraph", "Environment paragraph", "Stikstof assumptions",
                "Permit risk register", "Submission package", "Authority correspondence", "Permit dashboard",
                "Permit report export", "Permit evidence bundle",
            ],
            "S08": [
                "Cost structure", "Quantity engine", "Unit rates schema", "Cost estimate report",
                "Planning engine", "Milestone planner", "Tender package", "Scope breakdown",
                "Scenario costing", "GREX starter", "Financial feasibility", "Risk reserve",
                "Procurement strategy", "Contract document list", "Budget dashboard", "Planning dashboard",
                "Tender checklist", "Cost export Excel", "Cost report PDF", "Investment memo",
            ],
            "S09": [
                "DOCX report generator", "PDF report generator", "Excel export", "DXF export",
                "IFC export stub", "FreeCAD export", "SketchUp export plan", "Drawing register",
                "Situation drawing", "Floorplan drawing", "Elevation drawing", "Section drawing",
                "Foundation drawing", "Structural drawing", "3D view export", "Drawing PDF pack",
                "Report drawing integration", "Source appendix", "Project ZIP", "Export dashboard",
            ],
            "S10": [
                "Installer script", "Update script standard", "Patch manifest", "Release notes",
                "User manual", "Technical manual", "Developer guide", "Architecture spec",
                "API documentation", "Test project library", "Example Moskee project", "Example Plutostraat project",
                "Example Bruynzeel project", "Backup policy", "Restore policy", "Onboarding guide",
                "Troubleshooting guide", "Version archive", "Release dashboard", "Final acceptance checklist",
            ],
        }

        title = title_templates.get(track["id"], [f"{track['name']} task"])[index - 1]
        safe_title = title.lower().replace(" ", "_").replace("/", "_").replace("-", "_")

        return {
            "task_id": task_id,
            "track": track["name"],
            "track_id": track["id"],
            "priority": priority,
            "title": title,
            "objective": f"Bouw of documenteer '{title}' als gecontroleerde Phoenix-bouwtaak binnen spoor {track['id']}.",
            "files_to_create_or_modify": [
                f"apps/brewster_engineering_wizard/project_analyzer/{safe_title}.py",
                f"DOCS/project_phoenix/{track['id'].lower()}/{safe_title}.md",
                f"outputs/projects/{safe_title}_log.json",
                f"outputs/projects/{safe_title}_dashboard.html",
            ],
            "update_script": f"PROJECT_PHOENIX_{task_id.lower().replace('-', '_')}_{safe_title}_update.ps1",
            "test_command": f"python -m py_compile apps/brewster_engineering_wizard/project_analyzer/{safe_title}.py",
            "commit_message": f"feat: add {title.lower()} ({task_id})",
            "risk_level": self.risk_for(track["id"], index),
            "dependencies": self.dependencies_for(track["id"], index),
            "requires_go": True if index == 1 or track["id"] in ["S04", "S07"] else False,
            "expected_result": "Update script draait lokaal, dashboard/log worden aangemaakt, git status wordt getoond.",
            "status": self.initial_status(task_id),
        }

    def risk_for(self, track_id: str, index: int) -> str:
        if track_id in ["S04", "S07"] or index in [1, 8, 14, 20]:
            return "hoog"
        if track_id in ["S05", "S06", "S09"]:
            return "middel"
        return "laag"

    def dependencies_for(self, track_id: str, index: int) -> List[str]:
        if index == 1:
            return []
        return [f"{track_id}-{index - 1:03d}"]

    def initial_status(self, task_id: str) -> str:
        completed = {
            "S01-001",
            "S01-007",
            "S01-008",
            "S01-009",
            "S01-018",
            "S03-001",
            "S03-009",
            "S05-001",
            "S05-004",
            "S05-008",
            "S09-004",
        }
        if task_id in completed:
            return "gedeeltelijk_of_afgerond"
        return "open"

    def build_progress(self, roadmap: Dict[str, Any]) -> Dict[str, Any]:
        tasks = roadmap["tasks"]
        completed = [t for t in tasks if t["status"] == "gedeeltelijk_of_afgerond"]
        open_tasks = [t for t in tasks if t["status"] == "open"]

        by_track = []
        for track in roadmap["tracks"]:
            track_tasks = [t for t in tasks if t["track_id"] == track["id"]]
            track_completed = [t for t in track_tasks if t["status"] == "gedeeltelijk_of_afgerond"]
            pct = round((len(track_completed) / len(track_tasks)) * 100, 1) if track_tasks else 0
            by_track.append(
                {
                    "track_id": track["id"],
                    "track": track["name"],
                    "total_tasks": len(track_tasks),
                    "completed_or_partial": len(track_completed),
                    "open": len(track_tasks) - len(track_completed),
                    "progress_percent": pct,
                }
            )

        return {
            "status": "ACTIEF",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_tasks": len(tasks),
            "completed_or_partial": len(completed),
            "open_tasks": len(open_tasks),
            "overall_progress_percent": round((len(completed) / len(tasks)) * 100, 1),
            "current_phase": "Phoenix governance, roadmap en gecontroleerde taakplanning",
            "last_completed_version": "v7.5 CAD Drawing Export Engine",
            "by_track": by_track,
            "git_policy": "Na elke taak: git status, commit, push, git status, working tree clean.",
        }

    def build_next_go(self, roadmap: Dict[str, Any], progress: Dict[str, Any]) -> Dict[str, Any]:
        open_tasks = [t for t in roadmap["tasks"] if t["status"] == "open"]
        next_task = sorted(open_tasks, key=lambda item: item["priority"])[0] if open_tasks else {}

        return {
            "status": "ACTIEF",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "next_safe_step": next_task,
            "instruction": "Vraag gebruiker om GO voordat een nieuwe ingrijpende bouwstap wordt uitgevoerd.",
            "recommended_next_version": "v7.7",
            "recommended_next_engine": "Phoenix Task Executor / Build Script Factory",
            "reason": "Nu de roadmap bestaat, moet Phoenix automatisch per taak update-scripts kunnen voorbereiden.",
        }

    def build_dashboard(
        self,
        rules: Dict[str, Any],
        roadmap: Dict[str, Any],
        progress: Dict[str, Any],
        next_go: Dict[str, Any],
    ) -> str:
        track_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['track_id'])}</td>"
            f"<td>{self.esc(item['track'])}</td>"
            f"<td>{self.esc(item['completed_or_partial'])}/{self.esc(item['total_tasks'])}</td>"
            f"<td>{self.esc(item['progress_percent'])}%</td>"
            "</tr>"
            for item in progress["by_track"]
        )

        next_task = next_go["next_safe_step"]

        top_tasks = sorted(roadmap["tasks"], key=lambda item: item["priority"])[:25]
        task_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['task_id'])}</td>"
            f"<td>{self.esc(item['track'])}</td>"
            f"<td>{self.esc(item['title'])}</td>"
            f"<td>{self.esc(item['risk_level'])}</td>"
            f"<td>{self.esc(item['status'])}</td>"
            f"<td>{self.esc(item['requires_go'])}</td>"
            "</tr>"
            for item in top_tasks
        )

        rules_list = "".join(
            f"<li>{self.esc(key)}: {self.esc(value)}</li>"
            for key, value in rules["workflow_policy"].items()
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Dagstart / Build Governance v7.6</title>
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
<h1>Project Phoenix Dagstart / Build Governance v7.6</h1>
<p>Status: <strong>{self.esc(progress['status'])}</strong></p>
<p class="badge">Voortgang: {self.esc(progress['overall_progress_percent'])}%</p>
<p>Laatste afgeronde versie: <strong>{self.esc(progress['last_completed_version'])}</strong></p>
<p>Actuele fase: {self.esc(progress['current_phase'])}</p>
</section>

<section>
<h2>Volgende veilige GO-stap</h2>
<p><strong>{self.esc(next_task.get('task_id', ''))}</strong> — {self.esc(next_task.get('title', ''))}</p>
<p>{self.esc(next_task.get('objective', ''))}</p>
<p>Risico: <strong>{self.esc(next_task.get('risk_level', ''))}</strong></p>
<p>Commit: <code>{self.esc(next_task.get('commit_message', ''))}</code></p>
</section>

<section>
<h2>Werkregels</h2>
<ul>{rules_list}</ul>
</section>

<section>
<h2>Voortgang per spoor</h2>
<table>
<tr><th>Spoor</th><th>Naam</th><th>Afgerond/deels</th><th>Voortgang</th></tr>
{track_rows}
</table>
</section>

<section>
<h2>Eerste 25 taken</h2>
<table>
<tr><th>Taak</th><th>Spoor</th><th>Titel</th><th>Risico</th><th>Status</th><th>GO nodig</th></tr>
{task_rows}
</table>
</section>

<section>
<h2>Bestanden</h2>
<p><code>{self.esc(str(self.rules_path))}</code></p>
<p><code>{self.esc(str(self.roadmap_path))}</code></p>
<p><code>{self.esc(str(self.progress_path))}</code></p>
<p><code>{self.esc(str(self.next_go_path))}</code></p>
</section>
</main>
</body>
</html>
"""

    def build_documentation(
        self,
        rules: Dict[str, Any],
        roadmap: Dict[str, Any],
        progress: Dict[str, Any],
        next_go: Dict[str, Any],
    ) -> str:
        next_task = next_go["next_safe_step"]
        lines = [
            "# Project Phoenix Build Governance v7.6",
            "",
            "Deze specificatie legt de Brewster Engineering Wizard werkwijze vast als standaard voor Project Phoenix.",
            "",
            "## Hoofdregels",
            "",
        ]

        for key, value in rules["workflow_policy"].items():
            lines.append(f"- {key}: {value}")

        lines.extend([
            "",
            "## Repositorybeleid",
            "",
            f"- Hoofdrepository: {rules['repository_policy']['main_repository']}",
            f"- Branch: {rules['repository_policy']['main_branch']}",
            f"- Engine-laag: {rules['repository_policy']['engine_layer_path']}",
            "",
            "## Roadmap",
            "",
            f"- Aantal sporen: {len(roadmap['tracks'])}",
            f"- Aantal concrete taken: {len(roadmap['tasks'])}",
            f"- Voortgang: {progress['overall_progress_percent']}%",
            "",
            "## Volgende veilige GO-stap",
            "",
            f"- Taak: {next_task.get('task_id', '')}",
            f"- Titel: {next_task.get('title', '')}",
            f"- Doel: {next_task.get('objective', '')}",
            f"- Commit: {next_task.get('commit_message', '')}",
            "",
            "## Sporen",
            "",
        ])

        for track in roadmap["tracks"]:
            lines.append(f"- {track['id']} — {track['name']}")

        lines.append("")
        return "\n".join(lines)

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


BuildGovernanceEngine = PhoenixBuildGovernanceEngine
PhoenixRoadmapEngine = PhoenixBuildGovernanceEngine


def main() -> None:
    engine = PhoenixBuildGovernanceEngine()
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

Write-Host "PROJECT PHOENIX - BUILD GOVERNANCE v7.6" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_build_governance_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Build Governance Engine v7.6 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_daily_start_dashboard_v7_6.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

$RunnerBatContent = @'
@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - BUILD GOVERNANCE v7.6

python apps\brewster_engineering_wizard\project_analyzer\phoenix_build_governance_engine.py || goto error

if exist "outputs\projects\phoenix_daily_start_dashboard_v7_6.html" (
    start "" "outputs\projects\phoenix_daily_start_dashboard_v7_6.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Build Governance Engine v7.6 is gestopt.
git status
pause
exit /b 1
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $RunnerPs1 -Value $RunnerPs1Content -Encoding UTF8
Set-Content -Path $RunnerBat -Value $RunnerBatContent -Encoding ASCII

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Build Governance Connector"
    engine_version = "v7.6"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    engine_path = "$EnginePath"
    runner_ps1 = "$RunnerPs1"
    runner_bat = "$RunnerBat"
    repository_policy = "Alleen PROJECT-PHOENIX repository"
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole Phoenix Build Governance Engine..." -ForegroundColor Cyan
python -m py_compile .\apps\brewster_engineering_wizard\project_analyzer\phoenix_build_governance_engine.py

Write-Host "Run v7.6..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\scripts\START_PROJECTANALYSE_v7_6.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.6 UPDATE KLAAR" -ForegroundColor Green
