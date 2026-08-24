[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Manifest,
    [ValidateSet("inspect","dry-run","run")]
    [string]$Mode = "run",
    [string]$RepoPath = "C:\PROJECT-PHOENIX"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Runner = Join-Path $RepoPath "runners\PROJECT_PHOENIX_autonomous_build_orchestrator_v1_0.py"
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "Phoenix autonomous build orchestrator runner not found: $Runner"
}
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf)) {
    throw "Build manifest not found: $Manifest"
}

$OldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($OldPythonPath) {
    "$RepoPath$([IO.Path]::PathSeparator)$OldPythonPath"
} else {
    $RepoPath
}

try {
    & python $Runner --repo $RepoPath $Mode --manifest $Manifest
    if ($LASTEXITCODE -ne 0) {
        throw "Phoenix autonomous build orchestrator failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
