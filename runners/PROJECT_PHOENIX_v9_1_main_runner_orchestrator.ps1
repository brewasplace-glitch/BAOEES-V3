param(
    [ValidateSet("self-test","plan","execute")]
    [string]$Mode = "plan",
    [string]$Workflow = "platform_foundation",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_main_runner_orchestrator.py"

switch ($Mode) {
    "self-test" { python $Engine self-test }
    "plan" { python $Engine plan --workflow $Workflow }
    "execute" { python $Engine execute --workflow $Workflow --approval-token $ApprovalToken }
}
if ($LASTEXITCODE -ne 0) { throw "Phoenix Main Runner Orchestrator v9.1 is geblokkeerd of mislukt." }
git status
