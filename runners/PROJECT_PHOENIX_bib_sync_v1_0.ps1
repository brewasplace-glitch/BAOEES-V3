param(
 [ValidateSet("sync","validate","status","search")][string]$Action="status",
 [string]$Query="",
 [string]$Repo="C:\PROJECT-PHOENIX"
)
$ErrorActionPreference="Stop"
$Python=Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if(-not(Test-Path -LiteralPath $Python)){$Python=(Get-Command python.exe -ErrorAction Stop).Source}
$Engine=Join-Path $Repo "phoenix\knowledge\bib_auto_sync.py"
$env:PYTHONDONTWRITEBYTECODE="1"
if($Action-eq"search"){
 if([string]::IsNullOrWhiteSpace($Query)){throw "Query is required for search."}
 & $Python $Engine search --repo $Repo --mode head --query $Query
}else{
 & $Python $Engine $Action --repo $Repo --mode head
}
if($LASTEXITCODE-ne0){throw "Phoenix BIB $Action failed."}
