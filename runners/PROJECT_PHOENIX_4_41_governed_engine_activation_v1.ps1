[CmdletBinding(PositionalBinding=$false)]
param(
    [Parameter(Mandatory=$true)][string]$BundleDir,
    [Parameter(Mandatory=$true)][string[]]$ApprovedImplementationSha256,
    [Parameter(Mandatory=$true)][switch]$ApproveActivation,
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$BackupRoot = "C:\PXBK"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    throw $Message
}

function GitCall {
    param([Parameter(Mandatory=$true)][string[]]$GitArgs)
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try {
        $output=@(& git.exe -c core.longpaths=true -C $RepoRoot @GitArgs 2>&1)
        $exitCode=$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference=$oldPreference
    }
    if ($exitCode -ne 0) {
        throw "git $($GitArgs -join ' ') failed`n$($output -join "`n")"
    }
    return @($output | ForEach-Object { "$_" })
}

function Resolve-Python {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $resolved=& py.exe -3 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -ne 0) { Fail "Python 3 resolve failed" }
        return "$resolved".Trim()
    }
    $command=Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail "Python 3 not found"
}

function Run-Python {
    param([Parameter(Mandatory=$true)][string[]]$PyArgs)
    $pythonExe=Resolve-Python
    $oldPyPath=$env:PYTHONPATH
    $env:PYTHONPATH=$RepoRoot
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try {
        $output=@(& $pythonExe @PyArgs 2>&1)
        $exitCode=$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference=$oldPreference
        $env:PYTHONPATH=$oldPyPath
    }
    if ($exitCode -ne 0) {
        $output | ForEach-Object { Write-Host $_ }
        Fail "Python failed with exit code $exitCode"
    }
    return @($output | ForEach-Object { "$_" })
}

if (-not $ApproveActivation) { Fail "Explicit -ApproveActivation is required" }
if (-not (Test-Path -LiteralPath $BundleDir -PathType Container)) { Fail "Bundle directory not found" }

$Runner=Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_engine_activation_v1.py"
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) { Fail "Phase-7 activation runner not installed" }

Write-Host "`n=== GOVERNED ENGINE ACTIVATION PREFLIGHT ===" -ForegroundColor Cyan
$branch=((GitCall @("branch","--show-current")) -join "").Trim()
$head=((GitCall @("rev-parse","HEAD")) -join "").Trim()
$null=GitCall @("fetch","origin",$branch)
$origin=((GitCall @("rev-parse","origin/$branch")) -join "").Trim()
$status=@(GitCall @("status","--porcelain=v1","--untracked-files=all"))
if ($origin -ne $head) { Fail "Local/remote baseline mismatch" }
if ($status.Count -ne 0) { Fail "Governed activation requires clean repository" }

$verify=Run-Python @($Runner,"--repo-root",$RepoRoot,"--verify-bundle",$BundleDir)
$verified=(($verify -join "`n") | ConvertFrom-Json)
$tx=$verified.transaction
if ($tx.baseline -ne $head) { Fail "Activation bundle baseline mismatch" }
if ($tx.status -ne "READY_FOR_GOVERNED_INSTALL") { Fail "Activation transaction is not ready" }

Write-Host "ENGINE_ID=$($tx.engine_id)"
Write-Host "TRANSACTION_ID=$($tx.transaction_id)"
Write-Host "IMPLEMENTATION_SHA256=$($tx.implementation_sha256 | ConvertTo-Json -Compress)"

$approved=@($ApprovedImplementationSha256 | ForEach-Object { $_.ToLowerInvariant() } | Sort-Object -Unique)
$required=@($tx.implementation_sha256.PSObject.Properties.Value | ForEach-Object { "$($_)".ToLowerInvariant() } | Sort-Object -Unique)
if (($approved -join "|") -ne ($required -join "|")) { Fail "Approved implementation SHA256 set does not exactly match transaction" }

Write-Host "`n=== VERIFIED FULL BACKUP ===" -ForegroundColor Cyan
$stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir=Join-Path $BackupRoot ("PHOENIX_ENGINE_ACTIVATION_"+$stamp+"_"+$head.Substring(0,8))
$BackupRunner=Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_full_backup_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $BackupRunner -RepoRoot $RepoRoot -ExpectedHead $head -BackupRoot $BackupRoot -BackupDir $BackupDir
if ($LASTEXITCODE -ne 0) { Fail "Activation backup failed" }
$BackupReceipt=Join-Path $BackupDir "BACKUP_RECEIPT.json"
if (-not (Test-Path -LiteralPath $BackupReceipt -PathType Leaf)) { Fail "Activation backup receipt missing" }

Write-Host "`n=== APPLY EXACT ACTIVATION BUNDLE THROUGH UNIVERSAL GATEWAY ===" -ForegroundColor Cyan
$applyArgs=@($Runner,"--repo-root",$RepoRoot,"--apply-bundle",$BundleDir,"--backup-receipt",$BackupReceipt,"--explicit-approval")
foreach ($sha in $approved) {
    $applyArgs += @("--approved-sha",$sha)
}
$apply=Run-Python $applyArgs
$result=(($apply -join "`n") | ConvertFrom-Json)
$planned=@($result.planned_paths)
if ($planned.Count -lt 4) { Fail "Activation planned path set unexpectedly small" }

try {
    Write-Host "`n=== POST-APPLY VALIDATION ===" -ForegroundColor Cyan
    foreach ($path in $planned) {
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ($path -replace "/","\")) -PathType Leaf)) {
            Fail "Planned activation path missing after apply: $path"
        }
    }

    $statusNow=@(
        GitCall @("status","--porcelain=v1","--untracked-files=all") |
        ForEach-Object { if ($_.Length -ge 4) { $_.Substring(3).Trim().Replace("\","/") } } |
        Where-Object { $_ }
    )
    $unexpected=@($statusNow | Where-Object { $planned -notcontains $_ })
    if ($unexpected.Count -gt 0) { Fail "Unexpected activation scope: $($unexpected -join ', ')" }

    $null=GitCall (@("diff","--check","--") + $planned)

    $smoke=Run-Python @($Runner,"--repo-root",$RepoRoot,"--smoke-import",$tx.transaction_id)
    $smokeResult=(($smoke -join "`n") | ConvertFrom-Json)
    if ($smokeResult.status -ne "PASS") { Fail "Activated adapter smoke import failed" }
    Write-Host "ACTIVATED_ADAPTER_SMOKE_IMPORT=PASS" -ForegroundColor Green

    $phase5Test=Join-Path $RepoRoot "tests\automation\test_phoenix_441_universal_capability_executor_registry_v1.py"
    $phase7Test=Join-Path $RepoRoot "tests\automation\test_phoenix_441_governed_engine_activation_v1.py"
    Run-Python @($phase5Test) | Out-Null
    Run-Python @($phase7Test) | Out-Null

    $centralPolicy=Get-Content -LiteralPath (Join-Path $RepoRoot "configs\phoenix\autonomy_policy_v2.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $bibAllow=@($centralPolicy.known_bib_governance_side_effect_paths | ForEach-Object { "$_".ToLowerInvariant() })

    $null=GitCall (@("add","--") + $planned)
    $null=GitCall @("diff","--cached","--check")
    (GitCall @("commit","-m",("feat(engine): governed activation "+$tx.engine_id))) | ForEach-Object { Write-Host $_ }
    $commit=((GitCall @("rev-parse","HEAD")) -join "").Trim()

    $commitFiles=@(
        GitCall @("show","--name-only","--pretty=format:","HEAD") |
        ForEach-Object { "$_".Trim().Replace("\","/") } |
        Where-Object { $_ }
    )
    $unexpectedCommit=@($commitFiles | Where-Object {
        ($planned -notcontains $_) -and ($bibAllow -notcontains $_.ToLowerInvariant())
    })
    if ($unexpectedCommit.Count -gt 0) {
        Fail "Unexpected activation commit scope: $($unexpectedCommit -join ', ')"
    }
    Write-Host "ACTIVATION_COMMIT_SCOPE=PASS" -ForegroundColor Green

    $null=GitCall @("fetch","origin",$branch)
    $remoteBefore=((GitCall @("rev-parse","origin/$branch")) -join "").Trim()
    if ($remoteBefore -ne $head) { Fail "REMOTE_RACE_GUARD: origin changed before activation push" }
    (GitCall @("push","origin",$branch)) | ForEach-Object { Write-Host $_ }
    $null=GitCall @("fetch","origin",$branch)
    $remoteAfter=((GitCall @("rev-parse","origin/$branch")) -join "").Trim()
    if ($remoteAfter -ne $commit) { Fail "Activation push verification failed" }

    Run-Python @($Runner,"--repo-root",$RepoRoot,"--mark-activated",$tx.transaction_id,"--commit",$commit) | Out-Null

    $final=@(GitCall @("status","--porcelain=v1","--untracked-files=all"))
    if ($final.Count -ne 0) { Fail "Repository not clean after activation" }

    Write-Host "GOVERNED_ENGINE_ACTIVATION=PASS" -ForegroundColor Green
    Write-Host "ENGINE_ID=$($tx.engine_id)"
    Write-Host "ACTIVATION_COMMIT=$commit"
    Write-Host "REPOSITORY_END_STATE=CLEAN_SYNCED" -ForegroundColor Green
}
catch {
    Write-Host "ACTIVATION_FAILURE=$($_.Exception.Message)" -ForegroundColor Red
    $trackedConfigs=@(
        "configs/phoenix/engine_registry_v1.json",
        "configs/phoenix/capability_executor_registry_v1.json",
        "configs/phoenix/policy_bundle_manifest_v1.json"
    )
    & git.exe -C $RepoRoot restore --staged --worktree -- $trackedConfigs 2>$null
    foreach ($path in $planned) {
        if ($trackedConfigs -notcontains $path) {
            $full=Join-Path $RepoRoot ($path -replace "/","\")
            if (Test-Path -LiteralPath $full -PathType Leaf) { Remove-Item -LiteralPath $full -Force }
        }
    }
    Run-Python @($Runner,"--repo-root",$RepoRoot,"--mark-recovery",$tx.transaction_id) | Out-Null
    throw
}
