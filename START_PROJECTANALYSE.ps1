$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " PROJECT PHOENIX / BAOEES" -ForegroundColor Cyan
Write-Host " START PROJECTANALYSE v5.0" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptRoot

$OutputRoot = Join-Path $ScriptRoot "outputs\projects"
$RunLog = Join-Path $OutputRoot "START_PROJECTANALYSE_LOCAL_RUN_LOG.txt"
$TempStdOut = Join-Path $OutputRoot "START_PROJECTANALYSE_STDOUT.tmp"
$TempStdErr = Join-Path $OutputRoot "START_PROJECTANALYSE_STDERR.tmp"
$StartDashboard = Join-Path $OutputRoot "project_start_analysis_dashboard.html"
$Launcher = Join-Path $OutputRoot "index.html"

if (-not (Test-Path $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

if (Test-Path $TempStdOut) {
    Remove-Item $TempStdOut -Force
}

if (Test-Path $TempStdErr) {
    Remove-Item $TempStdErr -Force
}

$StartedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$PythonArguments = @(
    "-W",
    "ignore::RuntimeWarning",
    "-m",
    "baoees.project_analyzer.project_start_analysis_engine"
)

"============================================================" | Out-File $RunLog -Encoding UTF8
"PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v5.0" | Out-File $RunLog -Append -Encoding UTF8
"Gestart: $StartedAt" | Out-File $RunLog -Append -Encoding UTF8
"Projectmap: $ScriptRoot" | Out-File $RunLog -Append -Encoding UTF8
"Commando: python -W ignore::RuntimeWarning -m baoees.project_analyzer.project_start_analysis_engine" | Out-File $RunLog -Append -Encoding UTF8
"============================================================" | Out-File $RunLog -Append -Encoding UTF8
"" | Out-File $RunLog -Append -Encoding UTF8

Write-Host "Projectmap:" -ForegroundColor Yellow
Write-Host $ScriptRoot
Write-Host ""

Write-Host "START PROJECTANALYSE wordt uitgevoerd..." -ForegroundColor Green
Write-Host ""

try {
    $Process = Start-Process `
        -FilePath "python" `
        -ArgumentList $PythonArguments `
        -WorkingDirectory $ScriptRoot `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $TempStdOut `
        -RedirectStandardError $TempStdErr

    $ExitCode = $Process.ExitCode

    if (Test-Path $TempStdOut) {
        Get-Content $TempStdOut | Tee-Object -FilePath $RunLog -Append
    }

    if (Test-Path $TempStdErr) {
        $StdErrContent = Get-Content $TempStdErr

        if ($StdErrContent) {
            "" | Out-File $RunLog -Append -Encoding UTF8
            "STDERR:" | Out-File $RunLog -Append -Encoding UTF8
            $StdErrContent | Tee-Object -FilePath $RunLog -Append
        }
    }

    "" | Out-File $RunLog -Append -Encoding UTF8
    "ExitCode: $ExitCode" | Out-File $RunLog -Append -Encoding UTF8

    if ($ExitCode -ne 0) {
        Write-Host ""
        Write-Host "START PROJECTANALYSE is gestopt met foutcode: $ExitCode" -ForegroundColor Red
        "Status: FAILED" | Out-File $RunLog -Append -Encoding UTF8
        throw "Python-run gaf foutcode $ExitCode."
    }

    Write-Host ""
    Write-Host "START PROJECTANALYSE succesvol uitgevoerd." -ForegroundColor Green
    "Status: OPGESLAGEN" | Out-File $RunLog -Append -Encoding UTF8
}
catch {
    Write-Host ""
    Write-Host "FOUT tijdens START PROJECTANALYSE:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red

    "" | Out-File $RunLog -Append -Encoding UTF8
    "FOUT: $($_.Exception.Message)" | Out-File $RunLog -Append -Encoding UTF8

    Write-Host ""
    Write-Host "Controleer logbestand:" -ForegroundColor Yellow
    Write-Host $RunLog

    Write-Host ""
    Read-Host "Druk op Enter om dit venster te sluiten"
    exit 1
}

$FinishedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"" | Out-File $RunLog -Append -Encoding UTF8
"Afgerond: $FinishedAt" | Out-File $RunLog -Append -Encoding UTF8

Write-Host ""
Write-Host "Controle outputs..." -ForegroundColor Cyan

if (Test-Path $StartDashboard) {
    Write-Host "Start Dashboard gevonden." -ForegroundColor Green
    Start-Process $StartDashboard
}
else {
    Write-Host "Start Dashboard ontbreekt:" -ForegroundColor Red
    Write-Host $StartDashboard
}

if (Test-Path $Launcher) {
    Write-Host "Launcher gevonden." -ForegroundColor Green
    Start-Process $Launcher
}
else {
    Write-Host "Launcher ontbreekt:" -ForegroundColor Red
    Write-Host $Launcher
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " START PROJECTANALYSE v5.0 KLAAR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logbestand:" -ForegroundColor Yellow
Write-Host $RunLog
Write-Host ""
Write-Host "Hoofdcommando:" -ForegroundColor Yellow
Write-Host "python -W ignore::RuntimeWarning -m baoees.project_analyzer.project_start_analysis_engine"
Write-Host ""

if (Test-Path $TempStdOut) {
    Remove-Item $TempStdOut -Force
}

if (Test-Path $TempStdErr) {
    Remove-Item $TempStdErr -Force
}

Read-Host "Druk op Enter om dit venster te sluiten"