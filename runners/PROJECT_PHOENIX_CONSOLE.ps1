[CmdletBinding()]
param([string]$RepoRoot = "C:\PROJECT-PHOENIX")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) { throw "Repository not found: $RepoRoot" }
Set-Location -LiteralPath $RepoRoot
$Host.UI.RawUI.WindowTitle = "PROJECT PHOENIX - Development Console"
$ReportPath = Join-Path $RepoRoot "outputs\runtime\development_console\environment_report.json"
python -m phoenix.development_console.cli --repo-root $RepoRoot --json-output $ReportPath
if ($LASTEXITCODE -ne 0) { throw "Phoenix Development Console check failed." }
Write-Host ""
Write-Host "Phoenix Console is ready." -ForegroundColor Green
Write-Host "Use this external PowerShell window instead of the GitKraken terminal."
Write-Host ""
