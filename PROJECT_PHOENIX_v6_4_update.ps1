# PROJECT PHOENIX v6.4 UPDATE
# Doel: START_PROJECTANALYSE koppelen aan de volledige Project Phoenix flow.
# Geen handmatig Python knip- en plakwerk nodig.
#
# Gebruik:
# 1. Zet dit bestand in C:\BREWSTER-ENGINEERING-WIZARD
# 2. Run:
#    powershell -ExecutionPolicy Bypass -File .\PROJECT_PHOENIX_v6_4_update.ps1

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.4 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_4.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_4.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v6_4_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

if (Test-Path $BatPath) {
    $BackupBat = "$BatPath.backup_v6_4_$Timestamp"
    Copy-Item $BatPath $BackupBat -Force
    Write-Host "Backup gemaakt: $BackupBat" -ForegroundColor Yellow
}

if (Test-Path $Ps1Path) {
    $BackupPs1 = "$Ps1Path.backup_v6_4_$Timestamp"
    Copy-Item $Ps1Path $BackupPs1 -Force
    Write-Host "Backup gemaakt: $BackupPs1" -ForegroundColor Yellow
}

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.4
echo ============================================================
echo.

echo [1/7] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [2/7] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [3/7] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [4/7] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [5/7] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [6/7] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [7/7] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.4 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\projects\project_start_analysis_dashboard.html" (
    start "" "outputs\projects\project_start_analysis_dashboard.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.4 is gestopt.
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
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.4" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Steps = @(
    @{ Name = "Startanalyse"; Command = "baoees\project_analyzer\project_start_analysis_engine.py" },
    @{ Name = "Workflow"; Command = "baoees\project_analyzer\project_analyzer_workflow_engine.py" },
    @{ Name = "AAIE/BIB aannames"; Command = "baoees\project_analyzer\aaie_bib_assumption_loader.py" },
    @{ Name = "Projectrapportagepackage"; Command = "baoees\project_analyzer\project_report_bib_engine.py" },
    @{ Name = "DOCX/PDF export"; Command = "baoees\project_analyzer\project_report_export_engine.py" },
    @{ Name = "Evidence en projectpakket"; Command = "baoees\project_analyzer\project_package_evidence_engine.py" },
    @{ Name = "Launcher bridge en startdashboard"; Command = "baoees\project_analyzer\project_analyzer_launcher_bridge.py" }
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
Write-Host "PROJECT PHOENIX v6.4 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_start_analysis_dashboard.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status

'@

Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1RunnerContent -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1RunnerContent -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix START PROJECTANALYSE Connector"
    engine_version = "v6.4"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    start_projectanalyse_bat = "$BatPath"
    start_projectanalyse_ps1 = "$Ps1Path"
    versioned_bat = "$VersionedBatPath"
    versioned_ps1 = "$VersionedPs1Path"
    purpose = "Koppelt START_PROJECTANALYSE aan de volledige Project Phoenix flow inclusief dashboard, rapportage, evidence en projectpakket."
    steps = @(
        "project_start_analysis_engine.py",
        "project_analyzer_workflow_engine.py",
        "aaie_bib_assumption_loader.py",
        "project_report_bib_engine.py",
        "project_report_export_engine.py",
        "project_package_evidence_engine.py",
        "project_analyzer_launcher_bridge.py"
    )
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven:" -ForegroundColor Green
Write-Host " - START_PROJECTANALYSE.bat"
Write-Host " - START_PROJECTANALYSE.ps1"
Write-Host " - START_PROJECTANALYSE_v6_4.bat"
Write-Host " - START_PROJECTANALYSE_v6_4.ps1"
Write-Host " - outputs\projects\start_projectanalyse_v6_4_update_log.json"

Write-Host ""
Write-Host "Test START_PROJECTANALYSE_v6_4.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v6_4.ps1

Write-Host ""
Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "PROJECT PHOENIX v6.4 UPDATE KLAAR" -ForegroundColor Green
