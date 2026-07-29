param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository

$FreeCADCmd=$env:FREECAD_CMD
if(-not $FreeCADCmd -or -not(Test-Path -LiteralPath $FreeCADCmd -PathType Leaf)){
 throw "FREECAD_CMD is not configured or does not point to FreeCADCmd.exe."
}
$Output="outputs\runtime\open_source_engines_v5_0_0\freecad_acceptance"
& py -3 "phoenix\adapters\open_source\freecad_acceptance.py" `
 --executable $FreeCADCmd `
 --script "tools\freecad\phoenix_freecad_acceptance_macro.py" `
 --output $Output
if($LASTEXITCODE-ne 0){throw "FreeCAD acceptance failed."}
