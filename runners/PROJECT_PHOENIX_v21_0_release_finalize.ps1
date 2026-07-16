param(
    [ValidateSet("self-test","audit","plan")]
    [string]$Mode = "plan"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_release_finalization_engine_v21_0.py"

switch ($Mode) {
    "self-test" {
        python $Engine self-test
    }
    "audit" {
        python $Engine audit
    }
    "plan" {
        python $Engine plan `
            --version "v21.0" `
            --commit-message "feat: Phoenix Core v21.0 Autonomous Release and Git Finalization Engine"
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Release Finalization Engine v21.0 is mislukt."
}

git status
