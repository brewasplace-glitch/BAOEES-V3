param(
    [Parameter(Mandatory=$true)][string]$InputJson,
    [string]$OutputDir = "",
    [switch]$RunFreeCAD,
    [switch]$RunBlender
)
$ErrorActionPreference="Stop"
$Repo=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if(-not $OutputDir){
    $project=Get-Content -LiteralPath $InputJson -Raw|ConvertFrom-Json
    $safe=([string]$project.project_id)-replace'[^A-Za-z0-9_.-]','_'
    $OutputDir=Join-Path $Repo "outputs\runtime\tropical_residential_real_spatial_ifc_v1_0\$safe"
}
$python=Get-Command python -ErrorAction SilentlyContinue
if(-not $python){throw "Python 3 required; Phoenix will not install it automatically."}
$args=@("-m","phoenix.design.tropical_residential.real_cli","--input",$InputJson,"--output",$OutputDir)
if($RunFreeCAD){$args+="--run-freecad-if-available"}
if($RunBlender){$args+="--run-blender-if-available"}
Push-Location $Repo
try{
    $env:PYTHONDONTWRITEBYTECODE="1"
    & $python.Source @args
    if($LASTEXITCODE-ne0){throw "Real spatial/IFC engine failed with exit code $LASTEXITCODE"}
}finally{
    Pop-Location
}
