param(
    [ValidateSet("self-test","validate","dry-run","execute","resume","status")]
    [string]$Mode = "dry-run",
    [string]$PlanPath = ".\outputs\runtime\v14_0\ai_planner_plan_v14_0.json",
    [string]$ExecutionId = "phoenix-core-v15",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_execution_engine_v15_0.py"

switch ($Mode) {
    "self-test" { python $Engine self-test }
    "validate" { python $Engine validate --plan-path $PlanPath }
    "dry-run" { python $Engine dry-run --plan-path $PlanPath --execution-id $ExecutionId }
    "execute" { python $Engine execute --plan-path $PlanPath --execution-id $ExecutionId --approval-token $ApprovalToken }
    "resume" { python $Engine resume --plan-path $PlanPath --execution-id $ExecutionId --approval-token $ApprovalToken }
    "status" { python $Engine status --execution-id $ExecutionId }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Autonomous Execution Engine v15.0 is geblokkeerd of mislukt."
}

git status
