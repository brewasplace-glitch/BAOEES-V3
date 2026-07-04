$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.6" -ForegroundColor Cyan
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
Write-Host "PROJECT PHOENIX v6.6 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$KnowledgeDashboard = Join-Path $PSScriptRoot "outputs\bib\dashboards\brewster_knowledge_migration_dashboard_v6_6.html"

if (Test-Path $KnowledgeDashboard) {
    Start-Process $KnowledgeDashboard
}

git status
