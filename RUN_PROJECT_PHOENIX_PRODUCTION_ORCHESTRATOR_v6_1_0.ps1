param(
 [string]$Repository="C:\PROJECT-PHOENIX",
 [string]$Project="configs\projects\moskee_bunschoten_multi_engine_pilot_v6_1_0.json",
 [string]$Output="outputs\runtime\unified_multi_engine_production_orchestrator_v6_1_0"
)
$ErrorActionPreference="Stop"
Set-Location $Repository
$Python=(Get-Command python.exe -CommandType Application -All -ErrorAction Stop|
 Where-Object{$_.Path -notmatch "\\Microsoft\\WindowsApps\\" -and (Test-Path -LiteralPath $_.Path)}|
 Select-Object -First 1).Path
& $Python "runners\PROJECT_PHOENIX_unified_multi_engine_production_orchestrator_v6_1_0.py" `
 --repository $Repository --project $Project --output $Output
if($LASTEXITCODE-ne 0){throw "Production orchestrator failed: $LASTEXITCODE"}
