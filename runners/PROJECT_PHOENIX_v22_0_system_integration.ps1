param(
    [ValidateSet("self-test","discover","validate","health","plan")]
    [string]$Mode = "plan"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_system_integration_engine_v22_0.py"

python $Engine $Mode

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix System Integration Engine v22.0 is mislukt."
}

git status
