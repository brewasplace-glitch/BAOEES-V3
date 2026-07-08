$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - AUTOMATED TASK BUILDER v7.8" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_automated_task_builder_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Automated Task Builder Engine v7.8 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_automated_task_builder_dashboard_v7_8.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
