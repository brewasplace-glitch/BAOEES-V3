[CmdletBinding()]
param(
    [string]$RepoRoot="C:\PROJECT-PHOENIX",
    [ValidateSet("dry-run","low-risk-auto")][string]$Mode="dry-run",
    [string]$TaskTitle="Advance PHOENIX autonomous development foundation",
    [string]$Action="plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$Runner=Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_autonomous_development_foundation_v1.py"
if(-not(Test-Path -LiteralPath $Runner -PathType Leaf)){throw "Autonomy runner missing: $Runner"}

$Python=$null
if(Get-Command py.exe -ErrorAction SilentlyContinue){
    $Python="py.exe"
    & $Python -3 $Runner --repo-root $RepoRoot --mode $Mode --task-title $TaskTitle --action $Action
}else{
    $cmd=Get-Command python.exe -ErrorAction SilentlyContinue
    if(-not$cmd){throw "Python 3 not found"}
    & $cmd.Source $Runner --repo-root $RepoRoot --mode $Mode --task-title $TaskTitle --action $Action
}
if($LASTEXITCODE-ne0){throw "Autonomous cycle failed with exit code $LASTEXITCODE"}
