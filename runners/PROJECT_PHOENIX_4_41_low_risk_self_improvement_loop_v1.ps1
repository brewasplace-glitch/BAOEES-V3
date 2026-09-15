[CmdletBinding(PositionalBinding=$false)]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$BackupRoot = "C:\PXBK"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    throw $Message
}

function Invoke-Git {
    param([Parameter(Mandatory=$true)][string[]]$GitArgs)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = @(
            & git.exe -c core.longpaths=true -C $RepoRoot @GitArgs 2>&1
        )
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }

    if ($exitCode -ne 0) {
        throw "git $($GitArgs -join ' ') failed`n$($output -join "`n")"
    }
    return @($output | ForEach-Object { "$_" })
}

$branch = ((Invoke-Git @("branch","--show-current")) -join "").Trim()
$null = Invoke-Git @("fetch","origin",$branch)
$head = ((Invoke-Git @("rev-parse","HEAD")) -join "").Trim()
$origin = ((Invoke-Git @("rev-parse","origin/$branch")) -join "").Trim()
$status = @(Invoke-Git @("status","--porcelain=v1","--untracked-files=all"))

if ($branch -ne "project-phoenix") { Fail "Self-improvement requires project-phoenix" }
if ($head -ne $origin) { Fail "Self-improvement requires local/origin sync" }
if ($status.Count -ne 0) { Fail "Self-improvement requires clean main worktree" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = Join-Path $BackupRoot ("PHOENIX_4_41_SELF_" + $stamp + "_" + $head.Substring(0,8))
$BackupRunner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_full_backup_v1.ps1"

& powershell -NoProfile -ExecutionPolicy Bypass -File $BackupRunner `
    -RepoRoot $RepoRoot `
    -ExpectedHead $head `
    -BackupRoot $BackupRoot `
    -BackupDir $BackupDir

if ($LASTEXITCODE -ne 0) {
    Fail "Self-improvement backup gate failed"
}

$Receipt = Join-Path $BackupDir "BACKUP_RECEIPT.json"
if (-not (Test-Path -LiteralPath $Receipt -PathType Leaf)) {
    Fail "Self-improvement backup receipt missing"
}

$Runner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_low_risk_self_improvement_loop_v1.py"
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    Fail "Self-improvement Python runner missing"
}

if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    & py.exe -3 $Runner --repo-root $RepoRoot --expected-head $head --backup-receipt $Receipt
}
else {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { Fail "Python 3 not found" }
    & $python.Source $Runner --repo-root $RepoRoot --expected-head $head --backup-receipt $Receipt
}

if ($LASTEXITCODE -ne 0) {
    Fail "LOW-risk self-improvement cycle failed"
}

Write-Host "PHOENIX_LOW_RISK_SELF_IMPROVEMENT_LOOP_V1=PASS" -ForegroundColor Green
