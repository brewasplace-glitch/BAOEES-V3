param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [Parameter(Mandatory=$true)][string]$Plan,
    [string]$OutputRoot
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
$Plan = (Resolve-Path $Plan).Path

$argsList = @(
    "-m", "phoenix.autonomy.structural_independent_verification_v1_0",
    "--repository", $Repository,
    "--plan", $Plan
)
if ($OutputRoot) {
    $argsList += @("--output-root", $OutputRoot)
}

Set-Location $Repository
python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix structural independent verification did not reach a passing technical status."
}
