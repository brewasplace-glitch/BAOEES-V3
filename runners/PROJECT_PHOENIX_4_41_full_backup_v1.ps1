[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [Parameter(Mandatory=$true)][string]$ExpectedHead,
    [string]$BackupRoot = "C:\PXBK",
    [string]$BackupDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    throw $Message
}

function Invoke-GitAt {
    param(
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [Parameter(Mandatory=$true)][string[]]$GitArgs
    )

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = @(
            & git.exe -c core.longpaths=true -C $WorkingDirectory @GitArgs 2>&1
        )
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }

    if ($exitCode -ne 0) {
        throw "git -C $WorkingDirectory $($GitArgs -join ' ') failed`n$($output -join "`n")"
    }

    return @($output | ForEach-Object { "$_" })
}

function GitText {
    param([Parameter(Mandatory=$true)][string[]]$GitArgs)
    return @(Invoke-GitAt -WorkingDirectory $RepoRoot -GitArgs $GitArgs)
}

$branch = ((GitText @("branch","--show-current")) -join "").Trim()
$head = ((GitText @("rev-parse","HEAD")) -join "").Trim()
$null = GitText @("fetch","origin",$branch)
$origin = ((GitText @("rev-parse","origin/$branch")) -join "").Trim()
$status = @(GitText @("status","--porcelain=v1","--untracked-files=all"))

if ($branch -ne "project-phoenix") { Fail "Backup requires project-phoenix" }
if ($head -ne $ExpectedHead) { Fail "Backup HEAD mismatch" }
if ($origin -ne $ExpectedHead) { Fail "Backup origin mismatch" }
if ($status.Count -ne 0) {
    $status | ForEach-Object { Write-Host "BACKUP_DIRTY=$_" }
    Fail "Backup requires clean worktree"
}

if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupDir = Join-Path $BackupRoot ("P44_" + $stamp + "_" + $ExpectedHead.Substring(0,8))
}

$BackupDir = [System.IO.Path]::GetFullPath($BackupDir)
$RepoFull = [System.IO.Path]::GetFullPath($RepoRoot)
if ($BackupDir.StartsWith($RepoFull + "\",[System.StringComparison]::OrdinalIgnoreCase)) {
    Fail "Backup directory may not be inside repository"
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$Snapshot = Join-Path $BackupDir "repo"
$Bundle = Join-Path $BackupDir "PROJECT-PHOENIX_ALL_REFS.bundle"
$Receipt = Join-Path $BackupDir "BACKUP_RECEIPT.json"

if (Test-Path -LiteralPath $Snapshot) {
    Remove-Item -LiteralPath $Snapshot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Snapshot | Out-Null

Write-Host "BACKUP_DIR=$BackupDir"
Write-Host "BACKUP_SNAPSHOT_START=ACTIVE"

$roboArgs = @(
    $RepoRoot,
    $Snapshot,
    "/E",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/R:1",
    "/W:1",
    "/XJ",
    "/NP",
    "/NFL",
    "/NDL"
)

& robocopy.exe @roboArgs | Out-Host
$roboCode = $LASTEXITCODE
if ($roboCode -ge 8) {
    Fail "robocopy snapshot failed with exit code $roboCode"
}

if (-not (Test-Path -LiteralPath (Join-Path $Snapshot ".git"))) {
    Fail "Snapshot .git directory missing"
}

$snapshotHead = ((Invoke-GitAt -WorkingDirectory $Snapshot -GitArgs @("rev-parse","HEAD")) -join "").Trim()
if ($snapshotHead -ne $ExpectedHead) {
    Fail "Snapshot HEAD verification failed"
}
Write-Host "BACKUP_FULL_REPO_SNAPSHOT=PASS" -ForegroundColor Green

if (Test-Path -LiteralPath $Bundle) {
    Remove-Item -LiteralPath $Bundle -Force
}

$null = GitText @("bundle","create",$Bundle,"--all")
$bundleVerify = @(GitText @("bundle","verify",$Bundle))
Write-Host "POWERSHELL_NATIVE_STDERR_GATE=PASS" -ForegroundColor Green
Write-Host "BACKUP_GIT_BUNDLE_VERIFY=PASS" -ForegroundColor Green

$bundleSha = (Get-FileHash -LiteralPath $Bundle -Algorithm SHA256).Hash.ToLowerInvariant()

@(
    "branch=$branch",
    "head=$head",
    "origin=$origin"
) | Set-Content -LiteralPath (Join-Path $BackupDir "BASELINE.txt") -Encoding ASCII

GitText @("log","-1","--decorate=full","--stat") |
    Set-Content -LiteralPath (Join-Path $BackupDir "HEAD_LOG.txt") -Encoding UTF8
GitText @("remote","-v") |
    Set-Content -LiteralPath (Join-Path $BackupDir "REMOTES.txt") -Encoding UTF8
GitText @("worktree","list","--porcelain") |
    Set-Content -LiteralPath (Join-Path $BackupDir "WORKTREES.txt") -Encoding UTF8
GitText @("config","--local","--list","--show-origin") |
    Set-Content -LiteralPath (Join-Path $BackupDir "LOCAL_GIT_CONFIG.txt") -Encoding UTF8

$receiptObject = [ordered]@{
    schema = "PHOENIX_FULL_BACKUP_RECEIPT_V1"
    status = "PASS"
    created_at = (Get-Date).ToString("o")
    repo_root = $RepoRoot
    branch = $branch
    baseline = $ExpectedHead
    origin_head = $origin
    snapshot_path = $Snapshot
    snapshot_verified = $true
    bundle_path = $Bundle
    bundle_verified = $true
    bundle_sha256 = $bundleSha
    robocopy_exit_code = $roboCode
    powershell_native_stderr_gate = $true
}

$json = $receiptObject | ConvertTo-Json -Depth 5
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Receipt,$json,$utf8NoBom)

Write-Host "BACKUP_RECEIPT=$Receipt"
Write-Host "BACKUP_BUNDLE_SHA256=$bundleSha"
Write-Host "PHOENIX_FULL_BACKUP_V1=PASS" -ForegroundColor Green
