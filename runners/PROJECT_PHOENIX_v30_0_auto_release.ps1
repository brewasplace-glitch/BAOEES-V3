param([ValidateSet("self-test","validate","plan","audit","summary")][string]$Mode="summary")
$ErrorActionPreference="Stop"
$R=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $R
python ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_auto_release_pipeline_v30_0.py" $Mode
if($LASTEXITCODE -ne 0){throw "Phoenix Auto Release Pipeline v30.0 is mislukt."}
git status
