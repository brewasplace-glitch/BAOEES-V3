param(
    [ValidateSet("self-test","scan","learn","optimize")]
    [string]$Mode = "optimize"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_learning_engine_v17_0.py"

python $Engine $Mode

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Autonomous Learning Engine v17.0 is mislukt."
}

git status
