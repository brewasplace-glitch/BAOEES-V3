param(
    [ValidateSet("self-test","discover","bootstrap","integration-test","summary")]
    [string]$Mode = "summary"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python ".\phoenix\kernel\phoenix_kernel_v31_1.py" $Mode

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Kernel v31.1 is mislukt."
}

git status
