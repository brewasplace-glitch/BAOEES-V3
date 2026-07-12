param([ValidateSet("repair","validate","repair-and-validate")][string]$Mode="repair-and-validate")
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
python ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_runtime_registry_validator_v13_1.py" $Mode
if($LASTEXITCODE -ne 0){throw "Runtime Registry Validator v13.1 mislukt."}
git status
