# PROJECT PHOENIX v6.5 UPDATE
# Doel: Health Check / QAQC toevoegen aan START_PROJECTANALYSE.
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.5 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$HealthEnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\project_analysis_health_check_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_5.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_5.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v6_5_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $HealthEnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

if (Test-Path $HealthEnginePath) {
    Copy-Item $HealthEnginePath "$HealthEnginePath.backup_v6_5_$Timestamp" -Force
}

if (Test-Path $BatPath) {
    Copy-Item $BatPath "$BatPath.backup_v6_5_$Timestamp" -Force
}

if (Test-Path $Ps1Path) {
    Copy-Item $Ps1Path "$Ps1Path.backup_v6_5_$Timestamp" -Force
}

$HealthEngineContent = @'
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectAnalysisHealthCheckEngine:
    ENGINE_NAME = "Project Phoenix Project Analysis Health Check Engine"
    ENGINE_VERSION = "v6.5"

    def __init__(self) -> None:
        self.project_output_root = PROJECT_ROOT / "outputs" / "projects"
        self.health_log_path = self.project_output_root / "project_analysis_health_check_log.json"
        self.health_dashboard_path = self.project_output_root / "project_analysis_health_check_dashboard.html"

    def run(self) -> Dict[str, Any]:
        self.project_output_root.mkdir(parents=True, exist_ok=True)

        checks = self.build_checks()
        passed_count = len([item for item in checks if item["passed"]])
        failed_count = len(checks) - passed_count
        score = int(round((passed_count / len(checks)) * 100)) if checks else 0

        if score >= 95:
            status = "GOEDGEKEURD"
        elif score >= 80:
            status = "AANDACHTSPUNTEN"
        else:
            status = "ONVOLLEDIG"

        result = {
            "status": status,
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.project_output_root),
            "health_log_path": str(self.health_log_path),
            "health_dashboard_path": str(self.health_dashboard_path),
            "score_percent": score,
            "check_count": len(checks),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "checks": checks,
            "next_steps": self.build_next_steps(checks),
        }

        self.write_json(self.health_log_path, result)
        self.write_text(self.health_dashboard_path, self.build_dashboard(result))

        return result

    def required_paths(self) -> List[Dict[str, Any]]:
        return [
            {"name": "START_PROJECTANALYSE.bat", "category": "runner", "path": PROJECT_ROOT / "START_PROJECTANALYSE.bat"},
            {"name": "START_PROJECTANALYSE.ps1", "category": "runner", "path": PROJECT_ROOT / "START_PROJECTANALYSE.ps1"},
            {"name": "Start dashboard", "category": "dashboard", "path": self.project_output_root / "project_start_analysis_dashboard.html"},
            {"name": "Launcher bridge dashboard", "category": "dashboard", "path": self.project_output_root / "project_analyzer_launcher_bridge_dashboard.html"},
            {"name": "Launcher bridge log", "category": "log", "path": self.project_output_root / "project_analyzer_launcher_bridge_log.json"},
            {"name": "Project package manifest", "category": "package", "path": self.project_output_root / "project_package_manifest.json"},
            {"name": "Project package ZIP", "category": "package", "path": self.project_output_root / "PROJECT_PHOENIX_PROJECT_ANALYZER_PACKAGE.zip"},
            {"name": "Evidence dashboard", "category": "evidence", "path": self.project_output_root / "project_package_evidence_dashboard.html"},
            {"name": "Evidence log", "category": "evidence", "path": self.project_output_root / "project_package_evidence_log.json"},
            {"name": "Report DOCX", "category": "report", "path": self.project_output_root / "project_report_bib_report.docx"},
            {"name": "Report PDF", "category": "report", "path": self.project_output_root / "project_report_bib_report.pdf"},
            {"name": "Report export log", "category": "report", "path": self.project_output_root / "project_report_export_log.json"},
            {"name": "Bronvermelding log", "category": "bronvermelding", "path": self.project_output_root / "Bronvermelding_van_dit_project" / "bronvermelding_log.json"},
            {"name": "Bronvermelding README", "category": "bronvermelding", "path": self.project_output_root / "Bronvermelding_van_dit_project" / "README_Bronvermelding_van_dit_project.txt"},
        ]

    def build_checks(self) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []

        for index, item in enumerate(self.required_paths(), start=1):
            path = Path(item["path"])
            exists = path.exists()
            size_bytes = path.stat().st_size if exists else 0

            if exists:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            else:
                modified_at = ""

            checks.append(
                {
                    "check_id": f"HC-{index:03d}",
                    "name": item["name"],
                    "category": item["category"],
                    "path": str(path),
                    "relative_path": self.safe_relative_path(path),
                    "exists": exists,
                    "size_bytes": size_bytes,
                    "modified_at": modified_at,
                    "passed": exists and size_bytes > 0,
                    "message": "Aanwezig en gevuld." if exists and size_bytes > 0 else "Ontbreekt of leeg.",
                }
            )

        return checks

    def build_next_steps(self, checks: List[Dict[str, Any]]) -> List[str]:
        failed = [item for item in checks if not item["passed"]]

        if not failed:
            return [
                "Alle hoofdoutputs zijn aanwezig.",
                "Leg v6.5 vast met git add, commit en push.",
                "Project Phoenix kan door naar v6.6.",
            ]

        steps = ["Herstel ontbrekende of lege hoofdoutputs:"]

        for item in failed:
            steps.append(item["relative_path"])

        return steps

    def build_dashboard(self, result: Dict[str, Any]) -> str:
        rows: List[str] = []

        for item in result["checks"]:
            status = "OK" if item["passed"] else "ONTBREEKT"
            rows.append(
                "<tr>"
                f"<td>{self.esc(item['check_id'])}</td>"
                f"<td>{self.esc(item['name'])}</td>"
                f"<td>{self.esc(item['category'])}</td>"
                f"<td>{self.esc(status)}</td>"
                f"<td><code>{self.esc(item['relative_path'])}</code></td>"
                f"<td>{self.esc(item['message'])}</td>"
                "</tr>"
            )

        next_steps = "".join(
            f"<li>{self.esc(step)}</li>"
            for step in result["next_steps"]
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix Health Check v6.5</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px; }}
    section {{ background: #111827; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
    h1, h2 {{ color: #f8fafc; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border: 1px solid #334155; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #1e293b; }}
    code {{ color: #bfdbfe; }}
    .score {{ font-size: 34px; font-weight: bold; color: #86efac; }}
  </style>
</head>
<body>
<main>
  <section>
    <h1>Project Phoenix Health Check v6.5</h1>
    <p>Status: <strong>{self.esc(result["status"])}</strong></p>
    <p class="score">{self.esc(result["score_percent"])}% compleet</p>
  </section>
  <section>
    <h2>Samenvatting</h2>
    <p>Checks totaal: {self.esc(result["check_count"])}</p>
    <p>Geslaagd: {self.esc(result["passed_count"])}</p>
    <p>Aandachtspunten: {self.esc(result["failed_count"])}</p>
  </section>
  <section>
    <h2>Checks</h2>
    <table>
      <tr>
        <th>ID</th>
        <th>Onderdeel</th>
        <th>Categorie</th>
        <th>Status</th>
        <th>Pad</th>
        <th>Bericht</th>
      </tr>
      {"".join(rows)}
    </table>
  </section>
  <section>
    <h2>Volgende stappen</h2>
    <ul>{next_steps}</ul>
  </section>
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


ProjectHealthCheckEngine = ProjectAnalysisHealthCheckEngine
ProjectAnalyzerHealthCheck = ProjectAnalysisHealthCheckEngine
HealthCheckEngine = ProjectAnalysisHealthCheckEngine


def main() -> None:
    engine = ProjectAnalysisHealthCheckEngine()
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
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.5
echo ============================================================
echo.

echo [1/8] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [2/8] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [3/8] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [4/8] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [5/8] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [6/8] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [7/8] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [8/8] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.5 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\projects\project_analysis_health_check_dashboard.html" (
    start "" "outputs\projects\project_analysis_health_check_dashboard.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.5 is gestopt.
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
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.5" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Steps = @(
    @{ Name = "Startanalyse"; Command = "baoees\project_analyzer\project_start_analysis_engine.py" },
    @{ Name = "Workflow"; Command = "baoees\project_analyzer\project_analyzer_workflow_engine.py" },
    @{ Name = "AAIE/BIB aannames"; Command = "baoees\project_analyzer\aaie_bib_assumption_loader.py" },
    @{ Name = "Projectrapportagepackage"; Command = "baoees\project_analyzer\project_report_bib_engine.py" },
    @{ Name = "DOCX/PDF export"; Command = "baoees\project_analyzer\project_report_export_engine.py" },
    @{ Name = "Evidence en projectpakket"; Command = "baoees\project_analyzer\project_package_evidence_engine.py" },
    @{ Name = "Launcher bridge en startdashboard"; Command = "baoees\project_analyzer\project_analyzer_launcher_bridge.py" },
    @{ Name = "Health check"; Command = "baoees\project_analyzer\project_analysis_health_check_engine.py" }
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
Write-Host "PROJECT PHOENIX v6.5 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$HealthDashboard = Join-Path $PSScriptRoot "outputs\projects\project_analysis_health_check_dashboard.html"

if (Test-Path $HealthDashboard) {
    Start-Process $HealthDashboard
}

git status
'@

Set-Content -Path $HealthEnginePath -Value $HealthEngineContent -Encoding UTF8
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1RunnerContent -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1RunnerContent -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Health Check Connector"
    engine_version = "v6.5"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    health_engine = "$HealthEnginePath"
    start_projectanalyse_bat = "$BatPath"
    start_projectanalyse_ps1 = "$Ps1Path"
    versioned_bat = "$VersionedBatPath"
    versioned_ps1 = "$VersionedPs1Path"
    purpose = "Voegt Project Analysis Health Check toe aan de volledige START_PROJECTANALYSE flow."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven:" -ForegroundColor Green
Write-Host " - baoees\project_analyzer\project_analysis_health_check_engine.py"
Write-Host " - START_PROJECTANALYSE.bat"
Write-Host " - START_PROJECTANALYSE.ps1"
Write-Host " - START_PROJECTANALYSE_v6_5.bat"
Write-Host " - START_PROJECTANALYSE_v6_5.ps1"
Write-Host " - outputs\projects\start_projectanalyse_v6_5_update_log.json"

Write-Host ""
Write-Host "Syntaxcontrole health check engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\project_analysis_health_check_engine.py

Write-Host ""
Write-Host "Test START_PROJECTANALYSE_v6_5.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v6_5.ps1

Write-Host ""
Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "PROJECT PHOENIX v6.5 UPDATE KLAAR" -ForegroundColor Green
