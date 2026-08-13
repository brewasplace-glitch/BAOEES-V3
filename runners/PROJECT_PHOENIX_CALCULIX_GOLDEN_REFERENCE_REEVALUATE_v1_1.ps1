param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$RuntimeRoot
)
$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository
if (-not $RuntimeRoot) {
    $RuntimeRoot = Join-Path $Repository "projects\runtime\REFERENCE-MODELS\CALCULIX-ANALYTICAL-v1_0\calculix"
}
$Dat = Join-Path $RuntimeRoot "PHX_GOLDEN_BEAM_CCX.dat"
$Inp = Join-Path $RuntimeRoot "PHX_GOLDEN_BEAM_CCX.inp"
$Out = Join-Path $RuntimeRoot "calculix_reference_reevaluation_v1_1.json"
if (-not (Test-Path -LiteralPath $Dat)) { throw "DAT evidence missing: $Dat" }
if (-not (Test-Path -LiteralPath $Inp)) { throw "INP evidence missing: $Inp" }

python -m phoenix.integrations.calculix.reaction_equilibrium_hardening_v1_1 `
    --dat $Dat `
    --inp $Inp `
    --output $Out
if ($LASTEXITCODE -ne 0) { throw "CalculiX Golden Reference v1.1 reevaluation failed." }

Write-Host ""
Write-Host "CALCULIX GOLDEN REFERENCE EXISTING EVIDENCE REEVALUATION v1.1 COMPLETE" -ForegroundColor Green
Write-Host "LIVE CALCULIX STARTED: NO"
Write-Host "RAW SOLVER EVIDENCE MODIFIED: NO"
Write-Host "RESULT: $Out"
