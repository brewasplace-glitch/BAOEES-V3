$ErrorActionPreference = "Stop"

# PHOENIX_ACTIVE_CONSOLE_REGISTRATION_v1_1
try {
    $host.UI.RawUI.WindowTitle = "PROJECT PHOENIX - ACTIVE CONSOLE"
    if (-not ("PhoenixConsoleNative" -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class PhoenixConsoleNative {
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
}
"@ -ErrorAction Stop
    }
    $ConsoleHwnd = [PhoenixConsoleNative]::GetConsoleWindow().ToInt64()
    $ParentPid = $null
    try { $ParentPid = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID" -ErrorAction Stop).ParentProcessId } catch {}
    $ConsoleStateDir = Join-Path $PSScriptRoot "outputs\runtime\phoenix_console_bridge_v1_0"
    New-Item -ItemType Directory -Path $ConsoleStateDir -Force | Out-Null
    [ordered]@{
        schema_version = "phoenix.active-console/1.0"
        console_hwnd = $ConsoleHwnd
        launcher_pid = $PID
        parent_process_id = $ParentPid
        repository = $PSScriptRoot
        registered_utc = [DateTime]::UtcNow.ToString("o")
        title = "PROJECT PHOENIX - ACTIVE CONSOLE"
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ConsoleStateDir "active_console.json") -Encoding UTF8
} catch {
    Write-Host "PHOENIX CONSOLE REGISTRATION: WARNING - $($_.Exception.Message)" -ForegroundColor Yellow
}
# END PHOENIX_ACTIVE_CONSOLE_REGISTRATION_v1_1

Set-StrictMode -Version Latest

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Repo "runners\PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Phoenix Official Start v3.0.2 runner ontbreekt: $Runner"
}

python $Runner
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Official Start v3.0.2 kon niet worden geopend."
}
