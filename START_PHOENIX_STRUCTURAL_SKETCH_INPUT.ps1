param([int]$Port=8771)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=(Get-Command py -ErrorAction SilentlyContinue)
if($Python){ & $Python.Source -3 "runners/PROJECT_PHOENIX_structural_sketch_upload_app_v1_0_0.py" --port $Port; exit $LASTEXITCODE }
$Python=(Get-Command python -ErrorAction SilentlyContinue)
if(-not $Python){ throw "Python 3 was not found." }
& $Python.Source "runners/PROJECT_PHOENIX_structural_sketch_upload_app_v1_0_0.py" --port $Port
