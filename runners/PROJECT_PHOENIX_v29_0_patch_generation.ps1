param(
    [ValidateSet("self-test","analyze","manifest","test-matrix","bundle-plan","application-plan","summary")]
    [string]$Mode="summary"
)
$ErrorActionPreference="Stop"
$R=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $R
python ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_patch_generation_engine_v29_0.py" $Mode
if($LASTEXITCODE -ne 0){throw "Phoenix Autonomous Patch Generation Engine v29.0 is mislukt."}
git status
