param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Output
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\structural_canonicalization_v1_2"
}

python -m phoenix.autonomy.pat001_structural_canonicalization_adapter_hardening_v1_2 `
    --repository $Repository `
    --output $Output

if ($LASTEXITCODE -ne 0) {
    throw "PAT-001 Structural Canonicalization + CalculiX Adapter Registration + Harvest Hardening v1.2 failed."
}

Write-Host ""
Write-Host "PAT-001 STRUCTURAL CANONICALIZATION + ADAPTER HARDENING v1.2 COMPLETE" -ForegroundColor Green
Write-Host "LIVE SCIA STARTED: NO"
Write-Host "LIVE CALCULIX STARTED: NO"
Write-Host "SOURCE CONTRACT OVERWRITTEN: NO"
Write-Host "OUTPUT: $Output"
