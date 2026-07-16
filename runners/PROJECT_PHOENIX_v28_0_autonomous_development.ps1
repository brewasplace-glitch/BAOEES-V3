param([ValidateSet("self-test","analyze","propose","patch-plan","regression-plan","summary")][string]$Mode="summary")
$ErrorActionPreference="Stop"
$R=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $R
python ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_development_engine_v28_0.py" $Mode
if($LASTEXITCODE -ne 0){throw "Phoenix Autonomous Development Engine v28.0 is mislukt."}
git status
