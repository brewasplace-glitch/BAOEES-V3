$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - TASK AUTOPILOT v8.0" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Task Autopilot Engine v8.0 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
