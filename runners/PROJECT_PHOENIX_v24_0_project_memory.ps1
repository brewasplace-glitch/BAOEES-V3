param(
    [ValidateSet("self-test","snapshot","lessons","compare","recommend")]
    [string]$Mode = "recommend",
    [string]$ProjectId = "project-phoenix",
    [string]$OtherProjectId = "project-phoenix"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_project_memory_engine_v24_0.py"

switch ($Mode) {
    "self-test" {
        python $Engine self-test
    }
    "snapshot" {
        python $Engine snapshot --project-id $ProjectId
    }
    "lessons" {
        python $Engine lessons --project-id $ProjectId
    }
    "compare" {
        python $Engine compare `
            --left-project-id $ProjectId `
            --right-project-id $OtherProjectId
    }
    "recommend" {
        python $Engine recommend --project-id $ProjectId
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Project Memory Engine v24.0 is mislukt."
}

git status
