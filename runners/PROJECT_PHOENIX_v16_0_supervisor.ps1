param(
    [ValidateSet("self-test","health","inspect","recovery-plan","recover")]
    [string]$Mode = "recovery-plan",
    [string]$ExecutionId = "phoenix-core-v15",
    [string]$PlanPath = ".\outputs\runtime\v14_0\ai_planner_plan_v14_0.json",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot
$Supervisor = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_workflow_supervisor_v16_0.py"

switch ($Mode) {
    "self-test" { python $Supervisor self-test }
    "health" { python $Supervisor health }
    "inspect" { python $Supervisor inspect --execution-id $ExecutionId }
    "recovery-plan" { python $Supervisor recovery-plan --execution-id $ExecutionId }
    "recover" {
        python $Supervisor recover `
            --execution-id $ExecutionId `
            --plan-path $PlanPath `
            --approval-token $ApprovalToken
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Workflow Supervisor v16.0 is geblokkeerd of mislukt."
}

git status
