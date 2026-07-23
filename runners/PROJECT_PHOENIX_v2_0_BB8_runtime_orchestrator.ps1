[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
    throw "Project Phoenix repository was not found: $RepoRoot"
}

Push-Location -LiteralPath $RepoRoot
try {
    python -m phoenix.runtime_orchestrator.cli
    if ($LASTEXITCODE -ne 0) {
        throw "BB8 Runtime Orchestrator self-test failed."
    }
}
finally {
    Pop-Location
}
