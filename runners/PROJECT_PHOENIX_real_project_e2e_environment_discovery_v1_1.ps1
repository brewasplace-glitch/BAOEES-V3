
param(
  [string]$Repo="C:\PROJECT-PHOENIX",
  [string]$JsonOut=""
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$Python=Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if(-not(Test-Path -LiteralPath $Python)){
  $Python=(Get-Command python.exe -ErrorAction Stop).Source
}
$oldByte=$env:PYTHONDONTWRITEBYTECODE
$oldPath=$env:PYTHONPATH
try{
  $env:PYTHONDONTWRITEBYTECODE="1"
  if([string]::IsNullOrWhiteSpace($oldPath)){$env:PYTHONPATH=$Repo}
  else{$env:PYTHONPATH=$Repo+";"+$oldPath}
  $NativeArgs=@((Join-Path $Repo "phoenix\validation\real_project_e2e_environment_discovery.py"),"--repo",$Repo)
  if(-not[string]::IsNullOrWhiteSpace($JsonOut)){
    $NativeArgs+=@("--json-out",$JsonOut)
  }
  & $Python @NativeArgs
  if($LASTEXITCODE-ne0){throw "E2E runtime discovery failed."}
}finally{
  if($null-eq$oldByte){Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue}else{$env:PYTHONDONTWRITEBYTECODE=$oldByte}
  if($null-eq$oldPath){Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue}else{$env:PYTHONPATH=$oldPath}
}
