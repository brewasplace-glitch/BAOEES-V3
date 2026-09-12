[CmdletBinding()]
param([string]$RepoRoot="C:\PROJECT-PHOENIX",[int]$Port=8765,[switch]$RegisterAutoStart)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
function Fail([string]$Message){throw $Message}
function PythonExe{
 if(Get-Command py.exe -ErrorAction SilentlyContinue){$x=& py.exe -3 -c "import sys; print(sys.executable)";if($LASTEXITCODE-ne 0){Fail "Python resolve failed"};return "$x".Trim()}
 $c=Get-Command python.exe -ErrorAction SilentlyContinue;if($c){return $c.Source};Fail "Python 3 not found"
}
function Health([int]$P){try{$r=Invoke-RestMethod -Uri "http://127.0.0.1:$P/health" -TimeoutSec 2;if($r.service-eq "PHOENIX_DETV_CAD_SIDECAR"-and$r.status-eq"PASS"){return $r}}catch{};return $null}
$server=Join-Path $RepoRoot "phoenix\detv_cad_bridge\server.py";if(-not(Test-Path $server)){Fail "CAD sidecar server missing"}

$deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\cad_viewer_v1"
New-Item -ItemType Directory -Force -Path $deps|Out-Null
$py=PythonExe
$old=$ErrorActionPreference
$ErrorActionPreference="Continue"
try{
 $probe=@(& $py -c "import sys; sys.path.insert(0, r'$deps'); import PIL; print(PIL.__version__)" 2>&1)
 $probeCode=$LASTEXITCODE
}finally{$ErrorActionPreference=$old}
if($probeCode-ne0){
 Write-Host "PIL_RUNTIME=MISSING_INSTALL_LOCAL"
 $old=$ErrorActionPreference
 $ErrorActionPreference="Continue"
 try{
  $pip=@(& $py -m pip install --disable-pip-version-check --no-input --target $deps "Pillow==12.3.0" 2>&1)
  $pipCode=$LASTEXITCODE
 }finally{$ErrorActionPreference=$old}
 $pip|ForEach-Object{Write-Host $_}
 if($pipCode-ne0){Fail "Pillow runtime installation failed"}
}else{
 Write-Host "PIL_RUNTIME=EXISTING"
}
$old=$ErrorActionPreference
$ErrorActionPreference="Continue"
try{
 $verify=@(& $py -c "import sys; sys.path.insert(0, r'$deps'); import PIL, PIL.Image; print('PIL_IMPORT=PASS'); print('PILLOW_VERSION='+PIL.__version__)" 2>&1)
 $verifyCode=$LASTEXITCODE
}finally{$ErrorActionPreference=$old}
$verify|ForEach-Object{Write-Host $_}
if($verifyCode-ne0){Fail "Pillow runtime import verification failed"}

$h=Health $Port
if(-not$h){
 $py=PythonExe;$pw=Join-Path(Split-Path -Parent $py)"pythonw.exe";if(-not(Test-Path $pw)){$pw=$py}
 Start-Process -FilePath $pw -ArgumentList @($server,"--repo-root",$RepoRoot,"--port","$Port") -WindowStyle Hidden|Out-Null
 for($i=0;$i-lt 30;$i++){Start-Sleep -Milliseconds 250;$h=Health $Port;if($h){break}}
 if(-not$h){Fail "PHOENIX DE TV CAD sidecar did not become healthy"}
 Write-Host "DETV_CAD_SIDECAR=STARTED" -ForegroundColor Green
}else{Write-Host "DETV_CAD_SIDECAR=EXISTING" -ForegroundColor Green}
if($RegisterAutoStart){
 $py=PythonExe;$pw=Join-Path(Split-Path -Parent $py)"pythonw.exe";if(-not(Test-Path $pw)){$pw=$py}
 $cmd='"0" "1" --repo-root "2" --port 3' -f $pw,$server,$RepoRoot,$Port
 $key="HKCU:\Software\Microsoft\Windows\CurrentVersion\Run";New-Item -Path $key -Force|Out-Null;New-ItemProperty -Path $key -Name "PROJECT-PHOENIX-CAD-SIDECAR" -Value $cmd -PropertyType String -Force|Out-Null
 Write-Host "DETV_CAD_SIDECAR_AUTOSTART=REGISTERED_HKCU" -ForegroundColor Green
}
if(-not(Health $Port)){Fail "Final sidecar health failed"}
Write-Host "DETV_CAD_SIDECAR_HEALTH=PASS" -ForegroundColor Green
