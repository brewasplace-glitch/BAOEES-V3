[CmdletBinding()]
param([string]$RepoRoot="C:\PROJECT-PHOENIX",[Parameter(Mandatory=$true)][string]$Request,[switch]$KeepCandidate,[switch]$PublishCandidate)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$Runner=Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_low_risk_autonomous_execution_v1.py"
if(-not(Test-Path -LiteralPath $Runner -PathType Leaf)){throw "LOW-risk runner missing: $Runner"}
if(-not(Test-Path -LiteralPath $Request -PathType Leaf)){throw "Request JSON missing: $Request"}
$extra=@(); if($KeepCandidate){$extra+="--keep-candidate"}; if($PublishCandidate){$extra+="--publish-candidate"}
if(Get-Command py.exe -ErrorAction SilentlyContinue){& py.exe -3 $Runner --repo-root $RepoRoot --request $Request @extra}else{$cmd=Get-Command python.exe -ErrorAction SilentlyContinue; if(-not$cmd){throw "Python 3 not found"}; & $cmd.Source $Runner --repo-root $RepoRoot --request $Request @extra}
if($LASTEXITCODE-ne0){throw "LOW-risk execution failed with exit code $LASTEXITCODE"}
