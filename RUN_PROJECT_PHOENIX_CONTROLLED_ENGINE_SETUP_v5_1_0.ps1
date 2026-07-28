param(
 [ValidateSet("plan","install-ifcopenshell","register","detect")]
 [string]$Action="plan",
 [string]$Engine="",
 [string]$Source="",
 [string]$Sha256="",
 [string]$Repository="C:\PROJECT-PHOENIX"
)
$ErrorActionPreference="Stop"
Set-Location $Repository
switch($Action){
 "plan" {
  Get-Content "configs\phoenix\third_party_engine_registry_v5_1_0.json"
 }
 "install-ifcopenshell" {
  & py -3 "runners\PROJECT_PHOENIX_controlled_engine_setup_v5_1_0.py" install-ifcopenshell
  if($LASTEXITCODE-ne 0){throw "IfcOpenShell installation failed."}
 }
 "register" {
  if(-not $Engine -or -not $Source -or -not $Sha256){throw "Engine, Source and Sha256 are required."}
  & py -3 "runners\PROJECT_PHOENIX_controlled_engine_setup_v5_1_0.py" register --engine $Engine --source $Source --sha256 $Sha256
  if($LASTEXITCODE-ne 0){throw "Engine registration failed."}
 }
 "detect" {
  & powershell -ExecutionPolicy Bypass -File "RUN_PROJECT_PHOENIX_OPEN_SOURCE_ENGINE_DETECTION_v5_0_0.ps1"
 }
}
