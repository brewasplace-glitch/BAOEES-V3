param(
    [Parameter(Mandatory=$true)][string]$InputJson,
    [string]$RuntimeRoot = ""
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $RuntimeRoot) {
    $RuntimeRoot = Join-Path $Repo "projects\runtime"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python 3 required; Phoenix will not install it automatically."
}

Push-Location $Repo
try {
    $oldBC = $env:PYTHONDONTWRITEBYTECODE
    $oldPP = $env:PYTHONPATH
    try {
        $env:PYTHONDONTWRITEBYTECODE = "1"
        if ([string]::IsNullOrWhiteSpace($oldPP)) {
            $env:PYTHONPATH = $Repo
        } else {
            $env:PYTHONPATH = $Repo + [System.IO.Path]::PathSeparator + $oldPP
        }

        & $python.Source -m phoenix.design.tropical_residential.tropical_3d_detv_cli `
            --input $InputJson `
            --runtime-root $RuntimeRoot

        if ($LASTEXITCODE -ne 0) {
            throw "Tropical Residential Real 3D + DE TV pipeline returned $LASTEXITCODE"
        }
    }
    finally {
        if ($null -eq $oldBC) {
            Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONDONTWRITEBYTECODE = $oldBC
        }
        if ($null -eq $oldPP) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONPATH = $oldPP
        }
    }
}
finally {
    Pop-Location
}
