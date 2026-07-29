param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository
$Launcher="C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat"
$Out="outputs\runtime\open_source_engines_v5_0_0\qgis_acceptance"
New-Item -ItemType Directory -Path $Out -Force|Out-Null
$Input=(Resolve-Path $Out).Path+"\phoenix_qgis_acceptance_input.geojson"
$Output=(Resolve-Path $Out).Path+"\phoenix_qgis_acceptance_buffer.gpkg"
& py -3 "phoenix\adapters\open_source\qgis_acceptance_v5_3_6.py" prepare --input $Input
$Stdout="$Out\qgis_process_stdout.txt"
$Stderr="$Out\qgis_process_stderr.txt"
$CmdFile=Join-Path $Out "run_qgis_buffer.cmd"
$CmdLines=@(
 "@echo off",
 "call `"$Launcher`" run native:buffer -- INPUT=`"$Input`" DISTANCE=25 SEGMENTS=8 END_CAP_STYLE=0 JOIN_STYLE=0 MITER_LIMIT=2 DISSOLVE=false OUTPUT=`"$Output`"",
 "exit /b %ERRORLEVEL%"
)
Set-Content -LiteralPath $CmdFile -Value $CmdLines -Encoding ASCII
& cmd.exe /d /c $CmdFile 1>$Stdout 2>$Stderr
$Code=$LASTEXITCODE
& py -3 "phoenix\adapters\open_source\qgis_acceptance_v5_3_6.py" validate --launcher $Launcher --version "3.44.12" --input $Input --output $Output --process-exit-code $Code --stdout $Stdout --stderr $Stderr --record "$Out\qgis_engine_acceptance.json"
