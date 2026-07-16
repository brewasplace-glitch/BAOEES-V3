param(
    [ValidateSet("self-test","analyze","decide","plan","next-step")]
    [string]$Mode="plan",
    [string]$Objective="Continue building Project Phoenix safely and autonomously."
)
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Engine=".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_decision_planning_engine_v25_0.py"
python $Engine $Mode --objective $Objective
if($LASTEXITCODE -ne 0){throw "Phoenix Autonomous Decision & Planning Engine v25.0 is mislukt."}
git status
