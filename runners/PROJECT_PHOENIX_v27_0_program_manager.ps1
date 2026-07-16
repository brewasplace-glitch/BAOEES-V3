param(
    [ValidateSet("self-test","validate","assess","plan","summary")]
    [string]$Mode = "summary",
    [string]$ProgramId = "project-phoenix-core-program"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Engine = ".\apps\brewster_engineering_wizard\project_analyzer\phoenix_autonomous_program_manager_v27_0.py"
python $Engine $Mode --program-id $ProgramId
if ($LASTEXITCODE -ne 0) { throw "Phoenix Autonomous Program Manager v27.0 is mislukt." }
git status
