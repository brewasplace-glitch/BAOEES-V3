param(
    [ValidateSet("self-test","validate","plan","execute")]
    [string]$Mode = "plan",
    [string]$ProjectId = "phoenix-core-v20",
    [string]$Objective = "Run the complete Phoenix Core autonomous pipeline safely.",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_full_autonomous_project_engine_v20_0.py"

switch ($Mode) {
    "self-test" {
        python $Engine self-test
    }
    "validate" {
        python $Engine validate
    }
    "plan" {
        python $Engine plan --project-id $ProjectId --objective $Objective
    }
    "execute" {
        python $Engine execute `
            --project-id $ProjectId `
            --objective $Objective `
            --approval-token $ApprovalToken
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Full Autonomous Project Engine v20.0 is geblokkeerd of mislukt."
}

git status
