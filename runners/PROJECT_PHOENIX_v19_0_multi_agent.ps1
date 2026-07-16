param(
    [ValidateSet("self-test","plan","validate","execute","status")]
    [string]$Mode = "plan",
    [string]$Workflow = "phoenix_core_coordination",
    [string]$RunId = "phoenix-core-v19",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_multi_agent_orchestrator_v19_0.py"

switch ($Mode) {
    "self-test" { python $Engine self-test }
    "plan" { python $Engine plan --workflow $Workflow --run-id $RunId }
    "validate" { python $Engine validate --workflow $Workflow }
    "execute" { python $Engine execute --workflow $Workflow --run-id $RunId --approval-token $ApprovalToken }
    "status" { python $Engine status --run-id $RunId }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Multi-Agent Orchestrator v19.0 is geblokkeerd of mislukt."
}

git status
