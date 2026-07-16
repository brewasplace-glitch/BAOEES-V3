param(
    [ValidateSet("self-test","discover","validate","health","plan","summary")]
    [string]$Mode = "summary",
    [string]$WorkflowId = "phoenix_executive_core",
    [string]$RunId = "phoenix-core-v26"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_executive_controller_v26_0.py"

switch ($Mode) {
    "self-test" {
        python $Engine self-test
    }
    "discover" {
        python $Engine discover
    }
    "validate" {
        python $Engine validate --workflow-id $WorkflowId
    }
    "health" {
        python $Engine health
    }
    "plan" {
        python $Engine plan --workflow-id $WorkflowId --run-id $RunId
    }
    "summary" {
        python $Engine summary --workflow-id $WorkflowId
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Executive Controller v26.0 is mislukt."
}

git status
