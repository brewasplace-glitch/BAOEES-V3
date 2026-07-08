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
