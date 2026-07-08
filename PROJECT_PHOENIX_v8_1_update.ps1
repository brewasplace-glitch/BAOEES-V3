# PROJECT PHOENIX v8.1 UPDATE
# Runner Validation Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v8.1 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Dit script moet vanuit de root van de PROJECT-PHOENIX repository worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "apps\brewster_engineering_wizard\project_analyzer\runner_validation.py"
$ScriptDir = Join-Path $ProjectRoot "scripts"
$RunnerPs1 = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_1.ps1"
$RunnerBat = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_1.bat"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v8_1_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $RunnerPs1, $RunnerBat)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v8_1_$Timestamp" -Force
    }
}

$EngineContent = @'
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


class RunnerValidationEngine:
    ENGINE_NAME = "Project Phoenix Runner Validation Engine"
    ENGINE_VERSION = "v8.1"

    def __init__(self) -> None:
        self.scripts_dir = PROJECT_ROOT / "scripts"
        self.outputs = PROJECT_ROOT / "outputs" / "projects"
        self.docs = PROJECT_ROOT / "DOCS" / "project_phoenix" / "s01"

        self.report_path = self.outputs / "runner_validation_report_v8_1.json"
        self.log_path = self.outputs / "runner_validation_log_v8_1.json"
        self.dashboard_path = self.outputs / "runner_validation_dashboard_v8_1.html"
        self.doc_path = self.docs / "runner_validation_v8_1.md"

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        ps1_runners = sorted(self.scripts_dir.glob("START_PROJECTANALYSE_v*.ps1")) if self.scripts_dir.exists() else []
        bat_runners = sorted(self.scripts_dir.glob("START_PROJECTANALYSE_v*.bat")) if self.scripts_dir.exists() else []

        runner_checks: List[Dict[str, Any]] = []
        for path in ps1_runners + bat_runners:
            runner_checks.append(self.validate_runner(path))

        pair_checks = self.validate_runner_pairs(ps1_runners, bat_runners)
        summary = self.build_summary(runner_checks, pair_checks)

        report = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "scripts_dir": str(self.scripts_dir),
            "runner_counts": {
                "ps1": len(ps1_runners),
                "bat": len(bat_runners),
                "total": len(ps1_runners) + len(bat_runners),
            },
            "summary": summary,
            "runner_checks": runner_checks,
            "pair_checks": pair_checks,
            "policy": {
                "no_auto_fix": True,
                "no_auto_delete": True,
                "validation_only": True,
                "safe_to_run_without_commit": True,
            },
            "next_steps": self.next_steps(summary),
        }

        self.write_json(self.report_path, report)
        self.write_text(self.dashboard_path, self.build_dashboard(report))
        self.write_text(self.doc_path, self.build_documentation(report))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "report_path": str(self.report_path),
            "dashboard_path": str(self.dashboard_path),
            "documentation_path": str(self.doc_path),
            "total_runners": summary["total_runners"],
            "ok_runners": summary["ok_runners"],
            "warning_runners": summary["warning_runners"],
            "failed_runners": summary["failed_runners"],
            "missing_python_refs": summary["missing_python_refs"],
            "pair_warnings": summary["pair_warnings"],
        }

        self.write_json(self.log_path, result)
        return result

    def validate_runner(self, path: Path) -> Dict[str, Any]:
        text = self.read_text(path)
        suffix = path.suffix.lower()
        python_refs = self.extract_python_refs(text)
        python_ref_checks = [self.check_python_ref(ref) for ref in python_refs]

        issues: List[Dict[str, str]] = []

        if not text.strip():
            issues.append({"severity": "hoog", "issue": "Runnerbestand is leeg."})

        if suffix == ".ps1":
            if "Set-Location" not in text and "cd " not in text.lower():
                issues.append({"severity": "middel", "issue": "PowerShell-runner bevat geen duidelijke Set-Location/cd."})
            if "$LASTEXITCODE" not in text and "throw" not in text.lower():
                issues.append({"severity": "middel", "issue": "PowerShell-runner heeft geen duidelijke foutafhandeling."})

        if suffix == ".bat":
            if "cd /d" not in text.lower():
                issues.append({"severity": "middel", "issue": "BAT-runner bevat geen duidelijke cd /d naar projectroot."})
            if "goto error" not in text.lower():
                issues.append({"severity": "middel", "issue": "BAT-runner heeft geen goto error foutafhandeling."})

        for ref_check in python_ref_checks:
            if not ref_check["exists"]:
                issues.append(
                    {
                        "severity": "hoog",
                        "issue": f"Python-verwijzing ontbreekt: {ref_check['reference']}",
                    }
                )

        if not python_refs:
            issues.append({"severity": "laag", "issue": "Geen Python-engine verwijzing gevonden."})

        status = "OK"
        if any(item["severity"] == "hoog" for item in issues):
            status = "FAIL"
        elif issues:
            status = "WARN"

        return {
            "runner": str(path.relative_to(PROJECT_ROOT)),
            "type": suffix.replace(".", ""),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "status": status,
            "python_refs": python_ref_checks,
            "issues": issues,
        }

    def extract_python_refs(self, text: str) -> List[str]:
        refs: List[str] = []
        patterns = [
            r"python\s+([^\r\n]+?\.py)",
            r"python\.exe\s+([^\r\n]+?\.py)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                ref = match.group(1).strip().strip('"').strip("'")
                ref = ref.replace(".\\", "").replace("./", "")
                ref = ref.split(" || ")[0].strip()
                if ref and ref not in refs:
                    refs.append(ref)

        return refs

    def check_python_ref(self, ref: str) -> Dict[str, Any]:
        normalized = ref.replace("\\", "/").strip()
        target = PROJECT_ROOT / normalized

        return {
            "reference": ref,
            "normalized": normalized,
            "path": str(target),
            "exists": target.exists(),
            "type": "python_engine",
        }

    def validate_runner_pairs(self, ps1_runners: List[Path], bat_runners: List[Path]) -> List[Dict[str, Any]]:
        ps1_versions = {self.version_from_runner(path): path for path in ps1_runners}
        bat_versions = {self.version_from_runner(path): path for path in bat_runners}
        versions = sorted(set(ps1_versions.keys()) | set(bat_versions.keys()))

        checks: List[Dict[str, Any]] = []
        for version in versions:
            ps1 = ps1_versions.get(version)
            bat = bat_versions.get(version)
            status = "OK" if ps1 and bat else "WARN"
            checks.append(
                {
                    "version": version,
                    "status": status,
                    "ps1": str(ps1.relative_to(PROJECT_ROOT)) if ps1 else "",
                    "bat": str(bat.relative_to(PROJECT_ROOT)) if bat else "",
                    "issue": "" if status == "OK" else "PS1/BAT-paar is niet compleet.",
                }
            )

        return checks

    def version_from_runner(self, path: Path) -> str:
        match = re.search(r"v(\d+_\d+)", path.name)
        if match:
            return "v" + match.group(1)
        return path.stem

    def build_summary(self, runner_checks: List[Dict[str, Any]], pair_checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(runner_checks)
        ok = len([item for item in runner_checks if item["status"] == "OK"])
        warn = len([item for item in runner_checks if item["status"] == "WARN"])
        fail = len([item for item in runner_checks if item["status"] == "FAIL"])
        missing_refs = 0

        for item in runner_checks:
            missing_refs += len([ref for ref in item.get("python_refs", []) if not ref.get("exists")])

        pair_warnings = len([item for item in pair_checks if item.get("status") != "OK"])

        overall = "OK"
        if fail or missing_refs:
            overall = "FAIL"
        elif warn or pair_warnings:
            overall = "WARN"

        return {
            "overall_status": overall,
            "total_runners": total,
            "ok_runners": ok,
            "warning_runners": warn,
            "failed_runners": fail,
            "missing_python_refs": missing_refs,
            "pair_warnings": pair_warnings,
        }

    def next_steps(self, summary: Dict[str, Any]) -> List[str]:
        if summary["overall_status"] == "OK":
            return [
                "Runnerstructuur is valide.",
                "Commit en push v8.1 na controle.",
                "Ga daarna door naar v8.2 Runner Repair Advisor of Phoenix Main Runner Orchestrator.",
            ]

        return [
            "Bekijk runner_validation_dashboard_v8_1.html.",
            "Los ontbrekende Python-verwijzingen of runnerparen op.",
            "Draai v8.1 daarna opnieuw.",
            "Commit pas als git status en runnerstatus veilig zijn.",
        ]

    def build_dashboard(self, report: Dict[str, Any]) -> str:
        summary = report["summary"]

        runner_rows = "".join(
            "<tr>"
            f"<td><code>{self.esc(item.get('runner', ''))}</code></td>"
            f"<td>{self.esc(item.get('type', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td>{self.esc(len(item.get('python_refs', [])))}</td>"
            f"<td>{self.esc(len(item.get('issues', [])))}</td>"
            "</tr>"
            for item in report["runner_checks"]
        )

        pair_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('version', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td><code>{self.esc(item.get('ps1', ''))}</code></td>"
            f"<td><code>{self.esc(item.get('bat', ''))}</code></td>"
            f"<td>{self.esc(item.get('issue', ''))}</td>"
            "</tr>"
            for item in report["pair_checks"]
        )

        issue_rows = ""
        for item in report["runner_checks"]:
            for issue in item.get("issues", []):
                issue_rows += (
                    "<tr>"
                    f"<td><code>{self.esc(item.get('runner', ''))}</code></td>"
                    f"<td>{self.esc(issue.get('severity', ''))}</td>"
                    f"<td>{self.esc(issue.get('issue', ''))}</td>"
                    "</tr>"
                )

        if not issue_rows:
            issue_rows = "<tr><td colspan='3'>Geen issues gevonden.</td></tr>"

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Runner Validation v8.1</title>
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
<h1>Project Phoenix Runner Validation Engine v8.1</h1>
<p>Status: <strong>{self.esc(summary.get("overall_status", ""))}</strong></p>
<p class="badge">Runners: {self.esc(summary.get("total_runners", 0))}</p>
<p>OK: {self.esc(summary.get("ok_runners", 0))} | WARN: {self.esc(summary.get("warning_runners", 0))} | FAIL: {self.esc(summary.get("failed_runners", 0))}</p>
<p>Ontbrekende Python-verwijzingen: <strong>{self.esc(summary.get("missing_python_refs", 0))}</strong></p>
</section>

<section>
<h2>Runnerchecks</h2>
<table>
<tr><th>Runner</th><th>Type</th><th>Status</th><th>Python refs</th><th>Issues</th></tr>
{runner_rows}
</table>
</section>

<section>
<h2>PS1/BAT-paren</h2>
<table>
<tr><th>Versie</th><th>Status</th><th>PS1</th><th>BAT</th><th>Issue</th></tr>
{pair_rows}
</table>
</section>

<section>
<h2>Issues</h2>
<table>
<tr><th>Runner</th><th>Ernst</th><th>Issue</th></tr>
{issue_rows}
</table>
</section>
</main>
</body>
</html>
"""

    def build_documentation(self, report: Dict[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# Project Phoenix Runner Validation v8.1",
            "",
            "Deze engine controleert de start- en runner-scripts van Project Phoenix.",
            "",
            f"- Overall status: {summary.get('overall_status', '')}",
            f"- Totaal runners: {summary.get('total_runners', 0)}",
            f"- OK: {summary.get('ok_runners', 0)}",
            f"- WARN: {summary.get('warning_runners', 0)}",
            f"- FAIL: {summary.get('failed_runners', 0)}",
            f"- Ontbrekende Python-verwijzingen: {summary.get('missing_python_refs', 0)}",
            f"- Onvolledige runnerparen: {summary.get('pair_warnings', 0)}",
            "",
            "## Veiligheidsbeleid",
            "",
            "- v8.1 valideert alleen.",
            "- v8.1 wijzigt geen bestaande runnerbestanden.",
            "- v8.1 verwijdert niets.",
            "- herstel gebeurt pas in een volgende GO-stap.",
            "",
        ]
        return "\n".join(lines)

    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return ""

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


PhoenixRunnerValidationEngine = RunnerValidationEngine


def main() -> None:
    engine = RunnerValidationEngine()
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

Write-Host "PROJECT PHOENIX - RUNNER VALIDATION v8.1" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\runner_validation.py

if ($LASTEXITCODE -ne 0) {
    throw "Runner Validation Engine v8.1 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\runner_validation_dashboard_v8_1.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

$RunnerBatContent = @'
@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - RUNNER VALIDATION v8.1

python apps\brewster_engineering_wizard\project_analyzer\runner_validation.py || goto error

if exist "outputs\projects\runner_validation_dashboard_v8_1.html" (
    start "" "outputs\projects\runner_validation_dashboard_v8_1.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Runner Validation Engine v8.1 is gestopt.
git status
pause
exit /b 1
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $RunnerPs1 -Value $RunnerPs1Content -Encoding UTF8
Set-Content -Path $RunnerBat -Value $RunnerBatContent -Encoding ASCII

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Runner Validation Connector"
    engine_version = "v8.1"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    engine_path = "$EnginePath"
    runner_ps1 = "$RunnerPs1"
    runner_bat = "$RunnerBat"
    repository_policy = "Alleen PROJECT-PHOENIX repository"
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole Runner Validation Engine..." -ForegroundColor Cyan
python -m py_compile .\apps\brewster_engineering_wizard\project_analyzer\runner_validation.py

Write-Host "Run v8.1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\scripts\START_PROJECTANALYSE_v8_1.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v8.1 UPDATE KLAAR" -ForegroundColor Green
