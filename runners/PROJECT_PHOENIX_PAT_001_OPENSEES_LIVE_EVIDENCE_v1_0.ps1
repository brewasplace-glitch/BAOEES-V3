param(
    [string]$Repository = "C:\PROJECT-PHOENIX",
    [string]$Output,
    [string]$OpenSeesExecutable,
    [switch]$AllowLiveExecution,
    [int]$TimeoutSeconds = 180
)
$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path $Repository).Path
Set-Location $Repository
if (-not $Output) { $Output = Join-Path $Repository "projects\runtime\PHOENIX-PAT-001\structural_opensees_live_v1_0" }
$Arguments = @("-m","phoenix.autonomy.pat001_opensees_live_evidence_v1_0","--repository",$Repository,"--output",$Output,"--timeout","$TimeoutSeconds")
if ($OpenSeesExecutable) { $Arguments += @("--opensees-executable",$OpenSeesExecutable) }
if ($AllowLiveExecution) { $Arguments += "--allow-live-execution" }
python @Arguments
if ($LASTEXITCODE -ne 0) { throw "PAT-001 OpenSees live evidence runner failed." }
Write-Host ""
Write-Host "PAT-001 OPENSEES LIVE EXECUTION + RAW EVIDENCE + NORMALIZATION v1.0 COMPLETE" -ForegroundColor Green
Write-Host "ALLOW LIVE EXECUTION: $($AllowLiveExecution.IsPresent)"
Write-Host "SOURCE v8.3 DECKS OVERWRITTEN: NO"
Write-Host "PRODUCTION RELEASE: LOCKED"
Write-Host "FOR-CONSTRUCTION RELEASE: LOCKED"
Write-Host "OUTPUT: $Output"
