param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $Repository
& py -3 "runners\PROJECT_PHOENIX_open_source_engine_adapters_v5_0_0.py" detect
if($LASTEXITCODE-ne 0){throw "Engine detection failed."}
