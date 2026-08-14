param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$SourceContract,
    [string]$Output
)
$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $SourceContract) {
    $SourceContract = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\inputs\structural\pat001_structural_input_contract_v1_0.json"
}
if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\structural_bootstrap_v1_1"
}
if (-not (Test-Path -LiteralPath $SourceContract)) {
    throw "PAT-001 source contract missing: $SourceContract"
}

python -m phoenix.autonomy.pat001_structural_evidence_harvest_bootstrap_v1_1 `
    --repository $Repository `
    --source-contract $SourceContract `
    --output $Output

if ($LASTEXITCODE -ne 0) {
    throw "PAT-001 Structural Evidence Harvest + Contract Bootstrap v1.1 failed."
}

Write-Host ""
Write-Host "PAT-001 STRUCTURAL EVIDENCE HARVEST + CONTRACT BOOTSTRAP v1.1 COMPLETE" -ForegroundColor Green
Write-Host "LIVE SCIA STARTED: NO"
Write-Host "LIVE CALCULIX STARTED: NO"
Write-Host "SOURCE CONTRACT OVERWRITTEN: NO"
Write-Host "OUTPUT: $Output"
