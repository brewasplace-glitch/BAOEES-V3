param(
    [ValidateSet("self-test","plan","validate","execute","resume","status")]
    [string]$Mode = "plan",
    [string]$Workflow = "platform_foundation",
    [string]$ProjectId = "phoenix-core",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_workflow_engine.py"

switch ($Mode) {
    "self-test" { python $Engine self-test }
    "plan" { python $Engine plan --workflow $Workflow --project-id $ProjectId }
    "validate" { python $Engine validate --workflow $Workflow --project-id $ProjectId }
    "execute" { python $Engine execute --workflow $Workflow --project-id $ProjectId --approval-token $ApprovalToken }
    "resume" { python $Engine resume --workflow $Workflow --project-id $ProjectId --approval-token $ApprovalToken }
    "status" { python $Engine status --workflow $Workflow --project-id $ProjectId }
}
if ($LASTEXITCODE -ne 0) { throw "Phoenix Autonomous Workflow Engine v11.0 is geblokkeerd of mislukt." }
git status
