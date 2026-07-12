param(
    [ValidateSet("self-test","discover","validate-registry","select")]
    [string]$Mode = "discover",
    [string[]]$Capability = @("workflow.orchestration","engine.discovery","capability.registry")
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_engine_intelligence_v12_0.py"

switch ($Mode) {
    "self-test" { python $Engine self-test }
    "discover" { python $Engine discover }
    "validate-registry" { python $Engine validate-registry }
    "select" {
        $Arguments = @($Engine,"select")
        foreach ($Item in $Capability) { $Arguments += @("--capability",$Item) }
        python @Arguments
    }
}
if ($LASTEXITCODE -ne 0) { throw "Phoenix Core v12.0 Engine Intelligence is geblokkeerd of mislukt." }
git status
