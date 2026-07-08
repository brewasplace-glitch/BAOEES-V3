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
