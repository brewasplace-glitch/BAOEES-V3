param(
 [string]$Repository="C:\PROJECT-PHOENIX",
 [string]$Project="configs\projects\generic_building_architectural_program_v6_5_0.json",
 [string]$Output="outputs\runtime\parametric_architectural_generator_v6_5_0"
)
$ErrorActionPreference="Stop"
Set-Location $Repository
$Python=(Get-Command python.exe -CommandType Application -All -ErrorAction Stop |
 Where-Object {
  $_.Path -notmatch '\\Microsoft\\WindowsApps\\' -and
  (Test-Path -LiteralPath $_.Path -PathType Leaf)
 } | Select-Object -First 1).Path
& $Python "runners\PROJECT_PHOENIX_parametric_architectural_bim_drawing_generator_v6_5_0.py" `
 --project $Project --output $Output
if($LASTEXITCODE-ne 0){throw "Architectural generator failed: $LASTEXITCODE"}
