param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Contract,
    [string]$Output
)
$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository

if (-not $Contract) {
    $Contract = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\inputs\structural\pat001_structural_input_contract_v1_0.json"
}
if (-not $Output) {
    $Output = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\structural_preparation_v1_0"
}

python -m phoenix.autonomy.pat001_structural_preparation_v1_0 `
    --repository $Repository `
    --contract $Contract `
    --output $Output

if ($LASTEXITCODE -ne 0) {
    throw "PAT-001 Structural Preparation assessment failed."
}
