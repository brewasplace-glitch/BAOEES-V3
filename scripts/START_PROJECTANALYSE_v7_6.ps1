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
