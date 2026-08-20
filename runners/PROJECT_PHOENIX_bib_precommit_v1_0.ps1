param([string]$Repo="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($Repo)){$Repo=(& git rev-parse --show-toplevel).Trim()}
$Python=Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if(-not(Test-Path -LiteralPath $Python)){$Python=(Get-Command python.exe -ErrorAction Stop).Source}
$Engine=Join-Path $Repo "phoenix\knowledge\bib_auto_sync.py"
$env:PYTHONDONTWRITEBYTECODE="1"
& $Python $Engine sync --repo $Repo --mode git-index
if($LASTEXITCODE-ne0){throw "BIB pre-commit sync failed."}
& git -C $Repo add -- "bib/PHOENIX_AUTO_SYNC"
if($LASTEXITCODE-ne0){throw "BIB staging failed."}

# Machine-managed BIB files are generated with deterministic LF content. On Windows,
# Git may normalize the staged representation differently from the just-written
# worktree representation. Re-checkout the staged BIB into the worktree so the
# worktree matches the index before commit and cannot become dirty immediately after.
& git -C $Repo restore --worktree -- "bib/PHOENIX_AUTO_SYNC"
if($LASTEXITCODE-ne0){throw "BIB worktree reconciliation from staged index failed."}

$dirtyBib = @(& git -C $Repo diff --name-only -- "bib/PHOENIX_AUTO_SYNC" 2>$null)
if($LASTEXITCODE-ne0){throw "BIB worktree cleanliness check failed."}
if($dirtyBib.Count -gt 0){
    throw ("BIB worktree still differs from staged index: " + ($dirtyBib -join ", "))
}
Write-Host "BIB_WORKTREE_RECONCILIATION=PASS"

& $Python $Engine validate --repo $Repo --mode git-index
if($LASTEXITCODE-ne0){throw "BIB pre-commit validation failed."}
& git -C $Repo diff --cached --check
if($LASTEXITCODE-ne0){throw "git diff --cached --check failed after BIB sync."}
Write-Host "PHOENIX_BIB_PRECOMMIT=PASS"
