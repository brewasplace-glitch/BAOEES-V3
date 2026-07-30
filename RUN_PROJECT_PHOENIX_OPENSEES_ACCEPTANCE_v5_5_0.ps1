param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository
$Python=$env:OPENSEESPY_PYTHON
if(-not $Python){$Python=(py -3 -c "import sys;print(sys.executable)").Trim()}
& $Python "phoenix\adapters\open_source\opensees_acceptance_v5_5_0.py" --output "outputs\runtime\open_source_engines_v5_0_0\opensees_acceptance"
if($LASTEXITCODE-ne 0){throw "OpenSees acceptance failed"}
