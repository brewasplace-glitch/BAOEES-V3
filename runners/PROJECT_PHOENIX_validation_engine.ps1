[CmdletBinding()]
param(
    [string]$RepoRoot = (Get-Location).Path,
    [string]$Config = "configs/phoenix/validation_engine_default_v1_0.json",
    [string]$Output = "outputs/runtime/pve/validation_report.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$env:PYTHONPATH = $RepoRoot

python -m phoenix.validation_engine.cli `
    --repo-root $RepoRoot `
    --config $Config `
    --output $Output

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Validation Engine reported validation failures."
}
