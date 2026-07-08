$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - RUNNER VALIDATION v8.1" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\runner_validation.py

if ($LASTEXITCODE -ne 0) {
    throw "Runner Validation Engine v8.1 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\runner_validation_dashboard_v8_1.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
