param([string]$Repo = "C:\PROJECT-PHOENIX")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Engine = Join-Path $Repo "tools\start_screen\PROJECT_PHOENIX_official_start_v3_autosync.py"
if (-not (Test-Path $Engine)) { throw "Phoenix v3 AutoSync engine not found: $Engine" }
python $Engine --repo $Repo
if ($LASTEXITCODE -ne 0) { throw "Phoenix v3 AutoSync failed with exit code $LASTEXITCODE" }
