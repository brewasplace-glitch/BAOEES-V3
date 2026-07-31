param([string]$Repository="C:\PROJECT-PHOENIX")
Set-Location $Repository
python "runners\PROJECT_PHOENIX_real_project_execution_pipeline_v6_2_0.py" --repository $Repository --project "configs\projects\moskee_bunschoten_real_execution_pilot_v6_2_0.json" --output "outputs\runtime\real_project_execution_pipeline_v6_2_0"
if($LASTEXITCODE-ne 0){throw "Pipeline failed: $LASTEXITCODE"}
