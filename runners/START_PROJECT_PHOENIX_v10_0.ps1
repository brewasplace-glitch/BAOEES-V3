param(
    [ValidateSet("plan","execute","status","self-test")]
    [string]$Mode = "plan",
    [string]$Workflow = "platform_foundation",
    [string]$ApprovalToken = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$Kernel = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_kernel.py"

switch ($Mode) {
    "self-test" {
        python $Kernel self-test
    }
    "status" {
        python $Kernel status
    }
    "plan" {
        python $Kernel start-project --workflow $Workflow --mode plan
    }
    "execute" {
        python $Kernel start-project --workflow $Workflow --mode execute --approval-token $ApprovalToken
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Kernel v10.0 is geblokkeerd of mislukt."
}

git status
