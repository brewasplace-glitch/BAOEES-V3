[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InputManifest,
    [Parameter(Mandatory=$true)][string]$OutputManifest,
    [Parameter(Mandatory=$true)][string]$Report,
    [string]$RepoRoot='C:\PROJECT-PHOENIX'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Policy=Join-Path $RepoRoot 'configs\phoenix\r2d_r4_opening_policy.json'
$Engine=Join-Path $RepoRoot 'phoenix\architecture\r2d_r4_opening_rule_engine.py'
if(-not(Test-Path $Engine)){throw "R2D R4 engine not found: $Engine"}
if(-not(Test-Path $Policy)){throw "R2D R4 policy not found: $Policy"}
python $Engine $InputManifest $OutputManifest $Report --policy $Policy
if($LASTEXITCODE-ne0){throw "R2D R4 opening rule engine failed $LASTEXITCODE"}
