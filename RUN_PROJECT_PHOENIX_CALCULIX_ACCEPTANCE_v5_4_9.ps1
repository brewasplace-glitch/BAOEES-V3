param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository
$Executable=$env:CALCULIX_CCX_EXE
if(-not $Executable -or -not(Test-Path -LiteralPath $Executable -PathType Leaf)){
 throw "CALCULIX_CCX_EXE is not configured."
}
& py -3 "phoenix\adapters\open_source\calculix_acceptance_v5_4_9.py" `
 --executable $Executable `
 --output "outputs\runtime\open_source_engines_v5_0_0\calculix_acceptance" --package-version "2.23-1"
if($LASTEXITCODE-ne 0){throw "CalculiX acceptance failed."}
