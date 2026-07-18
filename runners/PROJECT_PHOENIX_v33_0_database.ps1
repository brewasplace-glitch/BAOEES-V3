param(
    [ValidateSet("self-test","integration-test","summary")]
    [string]$Mode = "summary"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python ".\phoenix\database\phoenix_unified_project_database_v33_0.py" $Mode
if ($LASTEXITCODE -ne 0) { throw "Phoenix Unified Project Database v33.0 is mislukt." }

git status
