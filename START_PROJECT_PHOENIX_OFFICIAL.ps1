$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Refresh = Join-Path $Repo "tools\start_screen\REFRESH_PROJECT_PHOENIX_OFFICIAL_START_v3.ps1"
$Legacy = Join-Path $Repo "START_PROJECT_PHOENIX_OFFICIAL_PRE_V3.ps1"

if (-not (Test-Path -LiteralPath $Refresh)) {
    throw "Phoenix v3 start-screen refresh hook missing: $Refresh"
}
if (-not (Test-Path -LiteralPath $Legacy)) {
    throw "Preserved pre-v3 official launcher missing: $Legacy"
}

& $Refresh -Repo $Repo
& $Legacy @args
