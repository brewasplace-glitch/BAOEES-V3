[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$RepoRoot = (Get-Location).Path,
    [string]$OutputDir = "releases/builds"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $Manifest)) {
    throw "Manifest not found: $Manifest"
}

$env:PYTHONPATH = $RepoRoot
python -m phoenix.release_builder.cli `
    --repo-root $RepoRoot `
    --manifest $Manifest `
    --output-dir $OutputDir

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Release Builder failed."
}
