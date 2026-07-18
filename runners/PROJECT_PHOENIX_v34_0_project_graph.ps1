param([ValidateSet("self-test","integration-test","demo")][string]$Mode = "integration-test")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
python ".\phoenix\graph\phoenix_project_graph_v34_0.py" $Mode
if ($LASTEXITCODE -ne 0) { throw "Phoenix Project Graph v34.0 is mislukt." }
git status
