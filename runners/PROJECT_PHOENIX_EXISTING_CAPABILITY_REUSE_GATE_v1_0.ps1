[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Spec,

    [string]$RepoPath = "C:\PROJECT-PHOENIX",

    [ValidateSet("REUSE","REPAIR","EXTEND","BUILD")]
    [string]$RequireDecision,

    [string]$Output
)

$ErrorActionPreference = "Stop"
$SpecPath = (Resolve-Path -LiteralPath $Spec).Path

$ArgsList = @(
    "-m",
    "phoenix.governance.existing_capability_reuse_gate",
    "--repo",
    $RepoPath,
    "--spec",
    $SpecPath
)

if ($RequireDecision) {
    $ArgsList += @("--require-decision", $RequireDecision)
}

if ($Output) {
    $OutputPath = [IO.Path]::GetFullPath($Output)
    $ArgsList += @("--output", $OutputPath)
}

Push-Location $RepoPath
try {
    & python @ArgsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
