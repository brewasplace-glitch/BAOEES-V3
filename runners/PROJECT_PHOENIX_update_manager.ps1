[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Manifest,[string]$RepoRoot=(Get-Location).Path,[string]$PlanOutput="outputs/runtime/pum/update_plan.json")
$ErrorActionPreference="Stop"
$env:PYTHONPATH=$RepoRoot
python -m phoenix.update_manager.cli --manifest $Manifest --plan-output $PlanOutput
if ($LASTEXITCODE -ne 0) { throw "Phoenix Update Manager planning failed." }
