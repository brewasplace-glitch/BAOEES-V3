# PROJECT PHOENIX v8.2 UPDATE
# Runner Repair Advisor Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v8.2 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Dit script moet vanuit de root van de PROJECT-PHOENIX repository worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "apps\brewster_engineering_wizard\project_analyzer\runner_repair_advisor.py"
$ScriptDir = Join-Path $ProjectRoot "scripts"
$RunnerPs1 = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_2.ps1"
$RunnerBat = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_2.bat"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v8_2_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $RunnerPs1, $RunnerBat)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v8_2_$Timestamp" -Force
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


class RunnerRepairAdvisorEngine:
    ENGINE_NAME = "Project Phoenix Runner Repair Advisor Engine"
    ENGINE_VERSION = "v8.2"

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "s01"

        self.validation_report_path = self.outputs / "runner_validation_report_v8_1.json"

        self.repair_plan_path = self.outputs / "runner_repair_advisor_plan_v8_2.json"
        self.repair_actions_path = self.outputs / "runner_repair_actions_v8_2.json"
        self.log_path = self.outputs / "runner_repair_advisor_log_v8_2.json"
        self.dashboard_path = self.outputs / "runner_repair_advisor_dashboard_v8_2.html"
        self.doc_path = self.docs / "runner_repair_advisor_v8_2.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")
        report = self.read_json(self.validation_report_path)

        actions = self.build_repair_actions(report)
        plan = self.build_repair_plan(report, actions)

        self.write_json(self.repair_plan_path, plan)
        self.write_json(self.repair_actions_path, {"status": "OPGESLAGEN", "actions": actions})
        self.write_text(self.dashboard_path, self.build_dashboard(plan))
        self.write_text(self.doc_path, self.build_documentation(plan))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "validation_report_path": str(self.validation_report_path),
            "repair_plan_path": str(self.repair_plan_path),
            "repair_actions_path": str(self.repair_actions_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
            "total_actions": len(actions),
            "high_priority_actions": len([a for a in actions if a.get("priority") == "hoog"]),
            "medium_priority_actions": len([a for a in actions if a.get("priority") == "middel"]),
            "low_priority_actions": len([a for a in actions if a.get("priority") == "laag"]),
            "go_required_for_repair": True,
        }

        self.write_json(self.log_path, result)
        return result

    def build_repair_actions(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions: List[Dict[str, Any]] = []

        if not report:
            actions.append(
                {
                    "action_id": "RRA-001",
                    "priority": "hoog",
                    "type": "missing_validation_report",
                    "title": "Runner validation report ontbreekt",
                    "problem": "runner_validation_report_v8_1.json is niet gevonden of niet leesbaar.",
                    "proposed_repair": "Run v8.1 Runner Validation opnieuw voordat herstel wordt voorbereid.",
                    "target_files": [],
                    "auto_fix_allowed_after_go": False,
                    "requires_go": True,
                }
            )
            return actions

        for check in report.get("runner_checks", []):
            runner = check.get("runner", "")
            status = check.get("status", "")

            if status == "FAIL":
                actions.append(
                    {
                        "action_id": self.next_action_id(actions),
                        "priority": "hoog",
                        "type": "runner_fail",
                        "title": "Runner heeft FAIL-status",
                        "problem": f"{runner} bevat één of meer kritieke issues.",
                        "proposed_repair": "Maak een gericht reparatiescript voor deze runner; overschrijf pas na GO.",
                        "target_files": [runner],
                        "auto_fix_allowed_after_go": True,
                        "requires_go": True,
                    }
                )

            if status == "WARN":
                actions.append(
                    {
                        "action_id": self.next_action_id(actions),
                        "priority": "middel",
                        "type": "runner_warning",
                        "title": "Runner heeft waarschuwingen",
                        "problem": f"{runner} bevat waarschuwingen.",
                        "proposed_repair": "Controleer foutafhandeling, Set-Location/cd en Python-verwijzingen.",
                        "target_files": [runner],
                        "auto_fix_allowed_after_go": True,
                        "requires_go": True,
                    }
                )

            for issue in check.get("issues", []):
                severity = issue.get("severity", "laag")
                priority = "hoog" if severity == "hoog" else "middel" if severity == "middel" else "laag"
                actions.append(
                    {
                        "action_id": self.next_action_id(actions),
                        "priority": priority,
                        "type": "runner_issue",
                        "title": issue.get("issue", "Runner issue"),
                        "problem": f"{runner}: {issue.get('issue', '')}",
                        "proposed_repair": self.proposed_issue_repair(issue.get("issue", "")),
                        "target_files": [runner],
                        "auto_fix_allowed_after_go": priority in ["hoog", "middel"],
                        "requires_go": True,
                    }
                )

            for ref in check.get("python_refs", []):
                if not ref.get("exists"):
                    actions.append(
                        {
                            "action_id": self.next_action_id(actions),
                            "priority": "hoog",
                            "type": "missing_python_reference",
                            "title": "Ontbrekende Python-engine verwijzing",
                            "problem": f"{runner} verwijst naar ontbrekend Python-bestand: {ref.get('reference', '')}",
                            "proposed_repair": "Maak ontbrekende engine aan of corrigeer runner-verwijzing naar bestaande engine.",
                            "target_files": [runner, ref.get("normalized", "")],
                            "auto_fix_allowed_after_go": True,
                            "requires_go": True,
                        }
                    )

        for pair in report.get("pair_checks", []):
            if pair.get("status") != "OK":
                target_files = []
                if pair.get("ps1"):
                    target_files.append(pair.get("ps1"))
                if pair.get("bat"):
                    target_files.append(pair.get("bat"))

                actions.append(
                    {
                        "action_id": self.next_action_id(actions),
                        "priority": "middel",
                        "type": "incomplete_runner_pair",
                        "title": "PS1/BAT-runnerpaar is niet compleet",
                        "problem": f"Runnerpaar {pair.get('version', '')} is niet compleet.",
                        "proposed_repair": "Genereer ontbrekende PS1- of BAT-runner op basis van bestaande partner.",
                        "target_files": target_files,
                        "auto_fix_allowed_after_go": True,
                        "requires_go": True,
                    }
                )

        if not actions:
            actions.append(
                {
                    "action_id": "RRA-001",
                    "priority": "laag",
                    "type": "no_repair_needed",
                    "title": "Geen runnerreparatie nodig",
                    "problem": "v8.1 heeft geen herstelpunten gevonden.",
                    "proposed_repair": "Geen actie nodig. Ga door naar de volgende roadmaptaak.",
                    "target_files": [],
                    "auto_fix_allowed_after_go": False,
                    "requires_go": False,
                }
            )

        return actions

    def proposed_issue_repair(self, issue: str) -> str:
        lowered = issue.lower()

        if "set-location" in lowered or "cd" in lowered:
            return "Voeg expliciete projectroot-locatie toe aan runner."
        if "foutafhandeling" in lowered or "goto error" in lowered or "lastexitcode" in lowered:
            return "Voeg foutafhandeling toe zodat runner stopt bij mislukte engine."
        if "python-verwijzing" in lowered or "ontbreekt" in lowered:
            return "Controleer of de Python-engine bestaat en corrigeer pad of maak engine aan."
        if "leeg" in lowered:
            return "Herbouw runnerbestand op basis van standaard Phoenix-runner template."

        return "Maak een gericht herstelvoorstel in v8.3; wijzig runner pas na GO."

    def build_repair_plan(self, report: Dict[str, Any], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        high = len([a for a in actions if a.get("priority") == "hoog"])
        medium = len([a for a in actions if a.get("priority") == "middel"])
        low = len([a for a in actions if a.get("priority") == "laag"])

        if high:
            status = "REPAIR_REQUIRED_HIGH"
        elif medium:
            status = "REPAIR_RECOMMENDED"
        else:
            status = "OK_OR_LOW_PRIORITY"

        return {
            "status": status,
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "validation_report_path": str(self.validation_report_path),
            "summary": {
                "total_actions": len(actions),
                "high_priority_actions": high,
                "medium_priority_actions": medium,
                "low_priority_actions": low,
                "go_required_for_actual_repair": True if high or medium else False,
                "validation_overall_status": report.get("summary", {}).get("overall_status", "UNKNOWN") if report else "MISSING",
            },
            "actions": actions,
            "repair_policy": {
                "advice_only": True,
                "no_files_changed": True,
                "no_auto_fix_in_v8_2": True,
                "actual_repair_requires_go": True,
                "next_engine": "v8.3 Runner Repair Patch Generator",
            },
            "next_steps": self.next_steps(status),
        }

    def next_steps(self, status: str) -> List[str]:
        if status == "REPAIR_REQUIRED_HIGH":
            return [
                "Bekijk runner_repair_advisor_dashboard_v8_2.html.",
                "Geef GO voor v8.3 Runner Repair Patch Generator.",
                "v8.3 mag pas na GO herstelpatches maken.",
            ]

        if status == "REPAIR_RECOMMENDED":
            return [
                "Bekijk runner_repair_advisor_dashboard_v8_2.html.",
                "Bepaal of runnerwaarschuwingen nu hersteld moeten worden.",
                "Ga eventueel door met v8.3.",
            ]

        return [
            "Geen urgente runnerreparatie nodig.",
            "Commit en push v8.2.",
            "Ga daarna door naar Phoenix Main Runner Orchestrator of volgende roadmaptaak.",
        ]

    def build_dashboard(self, plan: Dict[str, Any]) -> str:
        summary = plan.get("summary", {})

        action_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('action_id', ''))}</td>"
            f"<td>{self.esc(item.get('priority', ''))}</td>"
            f"<td>{self.esc(item.get('type', ''))}</td>"
            f"<td>{self.esc(item.get('title', ''))}</td>"
            f"<td>{self.esc(item.get('problem', ''))}</td>"
            f"<td>{self.esc(item.get('proposed_repair', ''))}</td>"
            "</tr>"
            for item in plan.get("actions", [])
        )

        if not action_rows:
            action_rows = "<tr><td colspan='6'>Geen acties.</td></tr>"

        next_steps = "".join(
            f"<li>{self.esc(item)}</li>"
            for item in plan.get("next_steps", [])
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Runner Repair Advisor v8.2</title>
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
<h1>Project Phoenix Runner Repair Advisor Engine v8.2</h1>
<p>Status: <strong>{self.esc(plan.get("status", ""))}</strong></p>
<p class="badge">Acties: {self.esc(summary.get("total_actions", 0))}</p>
<p>Hoog: {self.esc(summary.get("high_priority_actions", 0))} | Middel: {self.esc(summary.get("medium_priority_actions", 0))} | Laag: {self.esc(summary.get("low_priority_actions", 0))}</p>
<p>Werkelijke reparatie vereist GO: <strong>{self.esc(summary.get("go_required_for_actual_repair", ""))}</strong></p>
</section>

<section>
<h2>Herstelacties</h2>
<table>
<tr><th>ID</th><th>Prioriteit</th><th>Type</th><th>Titel</th><th>Probleem</th><th>Voorstel</th></tr>
{action_rows}
</table>
</section>

<section>
<h2>Volgende stappen</h2>
<ul>{next_steps}</ul>
</section>

<section>
<h2>Bestanden</h2>
<p><code>{self.esc(str(self.repair_plan_path))}</code></p>
<p><code>{self.esc(str(self.repair_actions_path))}</code></p>
</section>
</main>
</body>
</html>
"""

    def build_documentation(self, plan: Dict[str, Any]) -> str:
        summary = plan.get("summary", {})
        lines = [
            "# Project Phoenix Runner Repair Advisor v8.2",
            "",
            "Deze engine maakt hersteladvies op basis van v8.1 Runner Validation.",
            "",
            f"- Status: {plan.get('status', '')}",
            f"- Totaal acties: {summary.get('total_actions', 0)}",
            f"- Hoog: {summary.get('high_priority_actions', 0)}",
            f"- Middel: {summary.get('medium_priority_actions', 0)}",
            f"- Laag: {summary.get('low_priority_actions', 0)}",
            "",
            "## Veiligheidsbeleid",
            "",
            "- v8.2 geeft alleen advies.",
            "- v8.2 wijzigt geen runnerbestanden.",
            "- v8.2 verwijdert niets.",
            "- echte reparatie gebeurt pas na GO in v8.3.",
            "",
            "## Acties",
            "",
        ]

        for action in plan.get("actions", []):
            lines.append(f"- {action.get('action_id', '')} [{action.get('priority', '')}] {action.get('title', '')}: {action.get('proposed_repair', '')}")

        lines.append("")
        return "\n".join(lines)

    def next_action_id(self, actions: List[Dict[str, Any]]) -> str:
        return f"RRA-{len(actions) + 1:03d}"

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


PhoenixRunnerRepairAdvisorEngine = RunnerRepairAdvisorEngine


def main() -> None:
    engine = RunnerRepairAdvisorEngine()
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

Write-Host "PROJECT PHOENIX - RUNNER REPAIR ADVISOR v8.2" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\runner_repair_advisor.py

if ($LASTEXITCODE -ne 0) {
    throw "Runner Repair Advisor Engine v8.2 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\runner_repair_advisor_dashboard_v8_2.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

$RunnerBatContent = @'
@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - RUNNER REPAIR ADVISOR v8.2

python apps\brewster_engineering_wizard\project_analyzer\runner_repair_advisor.py || goto error

if exist "outputs\projects\runner_repair_advisor_dashboard_v8_2.html" (
    start "" "outputs\projects\runner_repair_advisor_dashboard_v8_2.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Runner Repair Advisor Engine v8.2 is gestopt.
git status
pause
exit /b 1
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $RunnerPs1 -Value $RunnerPs1Content -Encoding UTF8
Set-Content -Path $RunnerBat -Value $RunnerBatContent -Encoding ASCII

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Runner Repair Advisor Connector"
    engine_version = "v8.2"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    engine_path = "$EnginePath"
    runner_ps1 = "$RunnerPs1"
    runner_bat = "$RunnerBat"
    repository_policy = "Alleen PROJECT-PHOENIX repository"
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole Runner Repair Advisor Engine..." -ForegroundColor Cyan
python -m py_compile .\apps\brewster_engineering_wizard\project_analyzer\runner_repair_advisor.py

Write-Host "Run v8.2..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\scripts\START_PROJECTANALYSE_v8_2.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v8.2 UPDATE KLAAR" -ForegroundColor Green
