$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$module = Join-Path $root "phoenix\release\PhoenixReleaseFramework.psm1"

Import-Module $module -Force

$normalized = ConvertTo-NormalizedGitPath ".\outputs\graph\v34_0\graph.json"
if ($normalized -ne "outputs/graph/v34_0/graph.json") {
    throw "Padnormalisatie mislukt: $normalized"
}

$allowed = @(
    "outputs/graph/v34_0",
    "docs/automation/example.md"
)

if (-not (Test-PhoenixPathMatch `
    -Candidate "outputs/graph/v34_0/graph.json" `
    -AllowedPaths $allowed)) {
    throw "Runtime-bestand wordt niet correct herkend."
}

if (-not (Test-PhoenixPathMatch `
    -Candidate "OUTPUTS/GRAPH/V34_0/graph.json" `
    -AllowedPaths $allowed)) {
    throw "Hoofdletterongevoelige padmatching mislukt."
}

if (Test-PhoenixPathMatch `
    -Candidate "unexpected/file.txt" `
    -AllowedPaths $allowed) {
    throw "Onverwacht pad werd ten onrechte toegestaan."
}

Write-Host "Phoenix Release Framework v1.0 tests: PASS" -ForegroundColor Green

