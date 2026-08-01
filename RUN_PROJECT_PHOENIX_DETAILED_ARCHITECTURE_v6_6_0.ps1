param([string]$Repository="C:\PROJECT-PHOENIX")
Set-Location $Repository
python runners/PROJECT_PHOENIX_parametric_architectural_bim_drawing_generator_v6_5_0.py --project configs/projects/generic_building_architectural_program_v6_5_0.json --output outputs/runtime/parametric_architectural_generator_v6_5_0
if($LASTEXITCODE-ne 0){throw "Base generator failed"}
python runners/PROJECT_PHOENIX_detailed_architectural_element_opening_engine_v6_6_0.py --project configs/projects/generic_building_detailed_architecture_v6_6_0.json --architectural-model outputs/runtime/parametric_architectural_generator_v6_5_0/architectural_model.json --output outputs/runtime/detailed_architectural_elements_v6_6_0
if($LASTEXITCODE-ne 0){throw "Detailed engine failed"}
