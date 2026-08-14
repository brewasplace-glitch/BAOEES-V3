param(
    [ValidateSet("Assess","PrepareAll")][string]$Action,
    [string]$Repository="C:\PROJECT-PHOENIX",
    [string]$Output
)
$ErrorActionPreference="Stop"
$Repository=(Resolve-Path $Repository).Path
Set-Location $Repository
$Registry=Join-Path $Repository "configs\phoenix\structural\structural_golden_reference_suite_registry_v1_0.json"
if(-not $Output){$Output=Join-Path $Repository "projects\runtime\REFERENCE-MODELS\GOLDEN-SUITE-v1_0"}
if($Action-eq "Assess"){
    python -m phoenix.autonomy.structural_golden_reference_suite_v1_0 assess --repository $Repository --registry $Registry --output (Join-Path $Output "golden_reference_suite_assessment_v1_0.json")
}else{
    python -m phoenix.autonomy.structural_golden_reference_suite_v1_0 prepare-all --repository $Repository --registry $Registry --output (Join-Path $Output "calculix_prepared")
}
if($LASTEXITCODE-ne 0){throw "Golden Reference Suite action failed."}
