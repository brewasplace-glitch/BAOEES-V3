param(
    [ValidateSet("self-test","plan","validate")]
    [string]$Mode = "plan",
    [string]$ProjectId = "phoenix-core-v14",
    [string]$Objective = "Build the next safe Phoenix Core workflow.",
    [string[]]$Capability = @(
        "workflow.orchestration",
        "workflow.autonomous",
        "engine.discovery",
        "capability.registry"
    ),
    [string[]]$Constraint = @(
        "No automatic commit",
        "No automatic push",
        "Explicit GO before execution"
    ),
    [string]$PlanPath = ".\outputs\runtime\v14_0\ai_planner_plan_v14_0.json"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Planner = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_ai_planner_v14_0.py"

switch ($Mode) {
    "self-test" {
        python $Planner self-test
    }
    "plan" {
        $Args = @($Planner,"plan","--project-id",$ProjectId,"--objective",$Objective)
        foreach ($Item in $Capability) { $Args += @("--capability",$Item) }
        foreach ($Item in $Constraint) { $Args += @("--constraint",$Item) }
        python @Args
    }
    "validate" {
        python $Planner validate --plan-path $PlanPath
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix AI Planner v14.0 mislukt."
}

git status
