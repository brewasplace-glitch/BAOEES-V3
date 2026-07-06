$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.4" -ForegroundColor Cyan
$Steps = @(
    "baoees\project_analyzer\project_intake_engine.py",
    "baoees\project_analyzer\brewster_knowledge_migration_engine.py",
    "baoees\project_analyzer\deep_knowledge_harvest_engine.py",
    "baoees\project_analyzer\module_registry_engine.py",
    "baoees\project_analyzer\aaie_bib_assumption_loader.py",
    "baoees\project_analyzer\project_context_builder_engine.py",
    "baoees\project_analyzer\geotechniek_engine.py",
    "baoees\project_analyzer\foundation_engine.py",
    "baoees\project_analyzer\structural_engine.py",
    "baoees\project_analyzer\project_start_analysis_engine.py",
    "baoees\project_analyzer\project_analyzer_workflow_engine.py",
    "baoees\project_analyzer\project_report_bib_engine.py",
    "baoees\project_analyzer\project_report_export_engine.py",
    "baoees\project_analyzer\project_package_evidence_engine.py",
    "baoees\project_analyzer\project_analyzer_launcher_bridge.py",
    "baoees\project_analyzer\project_analysis_health_check_engine.py",
    "baoees\project_analyzer\project_error_diagnostics_engine.py",
    "baoees\project_analyzer\project_auto_repair_engine.py",
    "baoees\project_analyzer\project_analysis_health_check_engine.py"
)
$Index = 1
foreach ($Step in $Steps) {
    Write-Host "[$Index/$($Steps.Count)] $Step" -ForegroundColor Yellow
    python $Step
    if ($LASTEXITCODE -ne 0) { throw "Stap mislukt: $Step" }
    $Index++
}
Write-Host "PROJECT PHOENIX v7.4 START PROJECTANALYSE KLAAR" -ForegroundColor Green
$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_structural_dashboard_v7_4.html"
if (Test-Path $Dashboard) { Start-Process $Dashboard }
git status
