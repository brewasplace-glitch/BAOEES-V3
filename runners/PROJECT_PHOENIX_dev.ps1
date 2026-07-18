param(
    [ValidateSet("doctor","cleanup","test","status","validate-manifest")]
    [string]$Command = "status",

    [string]$Manifest = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if ($Command -eq "validate-manifest") {
    if (-not $Manifest) { throw "Manifestpad is verplicht." }
    python -m phoenix validate-manifest $Manifest
}
else {
    python -m phoenix $Command
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Development Workflow-opdracht mislukt."
}
