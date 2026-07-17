param(
    [ValidateSet("self-test","integration-test","summary")]
    [string]$Mode = "summary"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python ".\phoenix\digital_twin\phoenix_digital_twin_v32_0.py" $Mode

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Digital Twin v32.0 is mislukt."
}

git status
