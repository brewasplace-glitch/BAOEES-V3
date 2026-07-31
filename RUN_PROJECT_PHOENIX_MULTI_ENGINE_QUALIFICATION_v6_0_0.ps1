param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository
$Python=(Get-Command python.exe -CommandType Application -All -ErrorAction Stop |
 Where-Object{$_.Path -notmatch "\\Microsoft\\WindowsApps\\" -and (Test-Path $_.Path)} |
 Select-Object -First 1).Path
& $Python "runners\PROJECT_PHOENIX_multi_engine_qualification_v6_0_0.py" `
 --output "outputs\runtime\multi_engine_qualification_v6_0_0"
if($LASTEXITCODE-ne 0){throw "Multi-engine qualification failed: $LASTEXITCODE"}
