param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("inspect", "apply", "self-test")]
    [string]$Mode,

    [string]$Package = "",

    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_update_center.py"

switch ($Mode) {
    "self-test" {
        python $Engine self-test
    }
    "inspect" {
        if (-not $Package) {
            throw "Geef -Package met het pad naar een Phoenix ZIP-updatepakket."
        }
        python $Engine inspect --package $Package
    }
    "apply" {
        if (-not $Package) {
            throw "Geef -Package met het pad naar een Phoenix ZIP-updatepakket."
        }
        python $Engine apply --package $Package --approval-token $ApprovalToken
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Update Center v9.0 is geblokkeerd of mislukt."
}

git status
