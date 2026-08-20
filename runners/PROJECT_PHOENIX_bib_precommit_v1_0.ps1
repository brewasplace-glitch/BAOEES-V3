param([string]$Repo="")
$ErrorActionPreference="Stop"
if([string]::IsNullOrWhiteSpace($Repo)){$Repo=(& git rev-parse --show-toplevel).Trim()}
$Python=Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if(-not(Test-Path -LiteralPath $Python)){$Python=(Get-Command python.exe -ErrorAction Stop).Source}
$Engine=Join-Path $Repo "phoenix\knowledge\bib_auto_sync.py"
$env:PYTHONDONTWRITEBYTECODE="1"
& $Python $Engine sync --repo $Repo --mode git-index
if($LASTEXITCODE-ne0){throw "BIB pre-commit sync failed."}
& git -C $Repo add -- "BIB/PHOENIX_AUTO_SYNC"
if($LASTEXITCODE-ne0){throw "BIB staging failed."}
& $Python $Engine validate --repo $Repo --mode git-index
if($LASTEXITCODE-ne0){throw "BIB pre-commit validation failed."}
& git -C $Repo diff --cached --check
if($LASTEXITCODE-ne0){throw "git diff --cached --check failed after BIB sync."}
Write-Host "PHOENIX_BIB_PRECOMMIT=PASS"
