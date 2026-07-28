param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop";Set-Location $Repository
& py -3 "runners\PROJECT_PHOENIX_architectural_suite_v4_0_0.py" --model "configs\projects\moskee_bunschoten_architectural_model_v4_0_0.json" --output "outputs\runtime\architectural_suite_v4_0_0\moskee_bunschoten"
if($LASTEXITCODE-ne 0){throw "Architectural suite failed."}
