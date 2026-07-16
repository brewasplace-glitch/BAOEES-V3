param(
    [ValidateSet("self-test","inventory","audit","plan")]
    [string]$Mode = "plan"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_deterministic_release_engine_v23_0.py"
python $Engine $Mode

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Deterministic Release Engine v23.0 is mislukt."
}

git status
