param(
    [Parameter(Mandatory = $true)][string]$ProjectJson,
    [string]$Repo = "C:\PROJECT-PHOENIX"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Python 3 is required; Phoenix will not install it automatically."
    }
    $python = $cmd.Source
}

$runtimeRoot = Join-Path $Repo "projects\runtime"

$oldPP = $env:PYTHONPATH
$oldBC = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    if ([string]::IsNullOrWhiteSpace($oldPP)) {
        $env:PYTHONPATH = $Repo
    }
    else {
        $env:PYTHONPATH = $Repo + [IO.Path]::PathSeparator + $oldPP
    }

    & $python "-m" "phoenix.design.tropical_residential.project_orchestration_cli" `
        "--project-json" $ProjectJson `
        "--runtime-root" $runtimeRoot

    if ($LASTEXITCODE -ne 0) {
        throw "Phoenix autonomous architectural orchestration failed."
    }
}
finally {
    if ($null -eq $oldPP) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $oldPP
    }
    if ($null -eq $oldBC) {
        Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONDONTWRITEBYTECODE = $oldBC
    }
}
