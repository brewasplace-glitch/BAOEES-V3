[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [Parameter(Mandatory=$true)][string]$CandidateBranch,
    [Parameter(Mandatory=$true)][string]$ExpectedHead,
    [Parameter(Mandatory=$true)][string]$BackupReceipt
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Runner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_low_risk_mainline_promotion_v1.py"
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) { throw "Mainline promotion runner missing: $Runner" }
if (Get-Command py.exe -ErrorAction SilentlyContinue) { & py.exe -3 $Runner --repo-root $RepoRoot --candidate-branch $CandidateBranch --expected-head $ExpectedHead --backup-receipt $BackupReceipt }
else { $python = Get-Command python.exe -ErrorAction SilentlyContinue; if (-not $python) { throw "Python 3 not found" }; & $python.Source $Runner --repo-root $RepoRoot --candidate-branch $CandidateBranch --expected-head $ExpectedHead --backup-receipt $BackupReceipt }
if ($LASTEXITCODE -ne 0) { throw "LOW-risk mainline promotion failed with exit code $LASTEXITCODE" }
