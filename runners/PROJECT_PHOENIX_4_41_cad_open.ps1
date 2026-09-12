[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [ValidateSet("Open","Inspect","Convert")][string]$Mode = "Open",
    [string]$RepoRoot = "C:\PROJECT-PHOENIX"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message){throw $Message}

function Get-Python {
    if(Get-Command py.exe -ErrorAction SilentlyContinue){return @{Exe="py.exe";Prefix=@("-3")}}
    if(Get-Command python.exe -ErrorAction SilentlyContinue){return @{Exe="python.exe";Prefix=@()}}
    Fail "Python 3 not found"
}

$runtime = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\cad_viewer\cad_viewer_runtime.json"
$deps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\cad_viewer_v1"
$engine = Join-Path $RepoRoot "phoenix\cad_viewer\engine.py"

if(-not(Test-Path -LiteralPath $runtime -PathType Leaf)){Fail "CAD viewer runtime is not installed"}
if(-not(Test-Path -LiteralPath $engine -PathType Leaf)){Fail "Phoenix CAD viewer engine missing"}
if(-not(Test-Path -LiteralPath $FilePath -PathType Leaf)){Fail "CAD file missing: $FilePath"}

$ext=[System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()
if($ext -notin @(".dxf",".dwg")){Fail "Only DXF and DWG are supported"}

$env:PYTHONPATH="$RepoRoot;$deps"
$p=Get-Python

switch($Mode){
    "Open" {
        & $p.Exe @($p.Prefix) $engine --runtime-config $runtime --open $FilePath
    }
    "Inspect" {
        & $p.Exe @($p.Prefix) $engine --runtime-config $runtime --inspect $FilePath
    }
    "Convert" {
        if($ext -ne ".dwg"){Fail "Convert mode requires a DWG file"}
        & $p.Exe @($p.Prefix) $engine --runtime-config $runtime --convert-dwg $FilePath
    }
}

if($LASTEXITCODE-ne 0){Fail "Phoenix CAD viewer operation failed with exit code $LASTEXITCODE"}
