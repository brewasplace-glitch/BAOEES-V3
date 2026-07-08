$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - TASK EXECUTOR v7.7" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_executor_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Task Executor Engine v7.7 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_task_executor_dashboard_v7_7.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
