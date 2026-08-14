param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Output
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\structural_identity_v1_3"
}

python -m phoenix.autonomy.pat001_identity_closure_structural_preparation_state_v1_3 `
    --repository $Repository `
    --output $Output

if ($LASTEXITCODE -ne 0) {
    throw "PAT-001 Identity Closure + Structural Preparation State v1.3 failed."
}

Write-Host ""
Write-Host "PAT-001 IDENTITY CLOSURE + STRUCTURAL PREPARATION STATE v1.3 COMPLETE" -ForegroundColor Green
Write-Host "LIVE SCIA STARTED: NO"
Write-Host "LIVE CALCULIX STARTED: NO"
Write-Host "SOURCE CONTRACT OVERWRITTEN: NO"
Write-Host "OUTPUT: $Output"
