param([string]$Repository="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
$Root=Join-Path $Repository "inputs\third_party_engine_downloads_v5_1_0"
$Engines=@("ifcconvert","freecad","qgis","energyplus","opensees","calculix")
foreach($Engine in $Engines){
 $Dir=Join-Path $Root $Engine
 New-Item -ItemType Directory -Path $Dir -Force|Out-Null
 $Readme=Join-Path $Dir "PLACE_OFFICIAL_DOWNLOAD_HERE.txt"
 if(-not(Test-Path $Readme)){
  "Place the official or explicitly approved $Engine download/extracted folder here. Do not rename executables." | Set-Content -LiteralPath $Readme -Encoding UTF8
 }
}
Write-Host "ENGINE DOWNLOAD WORKSPACE CREATED: $Root" -ForegroundColor Green
