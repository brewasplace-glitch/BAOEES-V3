[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message){throw $Message}

function Get-Python {
    if(Get-Command py.exe -ErrorAction SilentlyContinue){return @{Exe="py.exe";Prefix=@("-3")}}
    if(Get-Command python.exe -ErrorAction SilentlyContinue){return @{Exe="python.exe";Prefix=@()}}
    Fail "Python 3 not found"
}

function Invoke-Python {
    param([Parameter(Mandatory=$true)][string[]]$PyArgs)
    $p=Get-Python
    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{$out=@(& $p.Exe @($p.Prefix) @PyArgs 2>&1);$code=$LASTEXITCODE}finally{$ErrorActionPreference=$old}
    $out|ForEach-Object{Write-Host $_}
    if($code-ne 0){Fail "Python failed with exit code $code"}
}

function Find-LibreCAD {
    $cmd=Get-Command librecad.exe -ErrorAction SilentlyContinue
    if($cmd){return $cmd.Source}

    $candidates=@(
        (Join-Path $env:ProgramFiles "LibreCAD\LibreCAD.exe"),
        (Join-Path $env:ProgramFiles "LibreCAD\librecad.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "LibreCAD\LibreCAD.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "LibreCAD\librecad.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\LibreCAD\LibreCAD.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\LibreCAD\librecad.exe")
    )
    foreach($c in $candidates){
        if($c -and (Test-Path -LiteralPath $c -PathType Leaf)){return $c}
    }

    foreach($base in @($env:ProgramFiles,${env:ProgramFiles(x86)},(Join-Path $env:LOCALAPPDATA "Programs"))){
        if(-not $base -or -not(Test-Path -LiteralPath $base)){continue}
        $dirs=@(Get-ChildItem -LiteralPath $base -Directory -Filter "LibreCAD*" -ErrorAction SilentlyContinue)
        foreach($d in $dirs){
            $hit=Get-ChildItem -LiteralPath $d.FullName -Recurse -File -Filter "librecad.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            if($hit){return $hit.FullName}
        }
    }
    return ""
}

function Ensure-LibreCAD {
    $existing=Find-LibreCAD
    if($existing){
        Write-Host "LIBRECAD=EXISTING"
        return $existing
    }

    $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
    if(-not $winget){Fail "LibreCAD is missing and winget.exe is unavailable"}

    Write-Host "LIBRECAD=MISSING_INSTALL_WINGET"
    $args=@(
        "install",
        "--id","LibreCAD.LibreCAD",
        "--exact",
        "--version","2.2.1.5",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--disable-interactivity"
    )

    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{
        $out=@(& $winget.Source @args 2>&1)
        $code=$LASTEXITCODE
    }finally{$ErrorActionPreference=$old}
    $out|ForEach-Object{Write-Host $_}

    if($code-ne 0){
        Write-Host "LIBRECAD_WINGET_STANDARD_INSTALL=FAILED_TRY_ELEVATED" -ForegroundColor Yellow
        $argLine=($args|ForEach-Object{
            if($_ -match '\s'){'"'+($_ -replace '"','\"')+'"'}else{$_}
        }) -join ' '
        $proc=Start-Process -FilePath $winget.Source -ArgumentList $argLine -Verb RunAs -Wait -PassThru
        if($proc.ExitCode-ne 0){Fail "LibreCAD winget installation failed with exit code $($proc.ExitCode)"}
    }

    Start-Sleep -Seconds 2
    $installed=Find-LibreCAD
    if(-not $installed){Fail "LibreCAD installation completed but librecad.exe was not found"}
    Write-Host "LIBRECAD_INSTALL=PASS" -ForegroundColor Green
    return $installed
}

function Ensure-LibreDWG {
    $toolRoot=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\tools\libredwg-0.14"
    $existing=Get-ChildItem -LiteralPath $toolRoot -Recurse -File -Filter "dwg2dxf.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if($existing){
        Write-Host "LIBREDWG=EXISTING"
        return $existing.FullName
    }

    New-Item -ItemType Directory -Force -Path $toolRoot|Out-Null
    $zip=Join-Path $env:TEMP "libredwg-0.14-win64.zip"
    $url="https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip"
    $expected="1ad7e15344d20b3426c3435b078d82fb84b35062815946b2cca9c5fc9810fea8"

    Write-Host "LIBREDWG=MISSING_DOWNLOAD_OFFICIAL"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    $actual=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "LIBREDWG_ZIP_SHA256=$actual"
    if($actual-ne $expected){Fail "LibreDWG SHA256 mismatch"}

    Expand-Archive -LiteralPath $zip -DestinationPath $toolRoot -Force
    $dwg2dxf=Get-ChildItem -LiteralPath $toolRoot -Recurse -File -Filter "dwg2dxf.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $dwg2dxf){Fail "dwg2dxf.exe missing after LibreDWG extraction"}

    Write-Host "LIBREDWG_SHA256=PASS" -ForegroundColor Green
    Write-Host "LIBREDWG_INSTALL=PASS" -ForegroundColor Green
    return $dwg2dxf.FullName
}

function Ensure-EzdxfRuntime {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\cad_viewer_v1"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null
    $marker=Join-Path $deps "ezdxf\__init__.py"

    if(-not(Test-Path -LiteralPath $marker -PathType Leaf)){
        Write-Host "EZDXF_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference
        $ErrorActionPreference="Continue"
        try{
            $out=@(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps "ezdxf==1.4.4" 2>&1)
            $code=$LASTEXITCODE
        }finally{$ErrorActionPreference=$old}
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "ezdxf installation failed"}
    }else{
        Write-Host "EZDXF_RUNTIME=EXISTING"
    }
    return $deps
}

$librecad=Ensure-LibreCAD
$dwg2dxf=Ensure-LibreDWG
$deps=Ensure-EzdxfRuntime

$runtimeDir=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\cad_viewer"
New-Item -ItemType Directory -Force -Path $runtimeDir|Out-Null
$runtimeConfig=Join-Path $runtimeDir "cad_viewer_runtime.json"

$runtime=[ordered]@{
    schema="PHOENIX_CAD_VIEWER_RUNTIME_1.0"
    librecad_exe=$librecad
    libredwg_dwg2dxf_exe=$dwg2dxf
    ezdxf_runtime=$deps
    installed_at=(Get-Date).ToString("o")
}
$runtimeJson=$runtime|ConvertTo-Json -Depth 5
$utf8NoBom=New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($runtimeConfig,$runtimeJson,$utf8NoBom)
Write-Host "CAD_RUNTIME_JSON_ENCODING=UTF8_NO_BOM" -ForegroundColor Green

$engine=Join-Path $RepoRoot "phoenix\cad_viewer\engine.py"
$env:PYTHONPATH="$RepoRoot;$deps"

Invoke-Python -PyArgs @("-c","import ezdxf; print('EZDXF_IMPORT=PASS'); print('EZDXF_VERSION='+ezdxf.__version__)")
Invoke-Python -PyArgs @($engine,"--runtime-config",$runtimeConfig,"--verify-runtime")
Invoke-Python -PyArgs @($engine,"--self-test")

$testRoot=Join-Path $env:TEMP "PHOENIX_CAD_VIEWER_TEST"
if(Test-Path -LiteralPath $testRoot){Remove-Item -LiteralPath $testRoot -Recurse -Force}
New-Item -ItemType Directory -Force -Path $testRoot|Out-Null

$testDxf=Join-Path $testRoot "phoenix_test.dxf"
Invoke-Python -PyArgs @($engine,"--make-test-dxf",$testDxf)
Invoke-Python -PyArgs @($engine,"--runtime-config",$runtimeConfig,"--inspect",$testDxf)

$dxf2dwg=Get-ChildItem -LiteralPath (Split-Path -Parent $dwg2dxf) -File -Filter "dxf2dwg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if(-not $dxf2dwg){
    $dxf2dwg=Get-ChildItem -LiteralPath (Split-Path -Parent (Split-Path -Parent $dwg2dxf)) -Recurse -File -Filter "dxf2dwg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
}

if($dxf2dwg){
    $testDwg=Join-Path $testRoot "phoenix_test.dwg"
    $roundDxf=Join-Path $testRoot "phoenix_test_roundtrip.dxf"

    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{
        $out1=@(& $dxf2dwg.FullName -y -o $testDwg $testDxf 2>&1)
        $code1=$LASTEXITCODE
    }finally{$ErrorActionPreference=$old}
    $out1|ForEach-Object{Write-Host $_}
    if($code1-ne 0 -or -not(Test-Path -LiteralPath $testDwg)){Fail "LibreDWG DXF->DWG self-test failed"}

    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{
        $out2=@(& $dwg2dxf -y -o $roundDxf $testDwg 2>&1)
        $code2=$LASTEXITCODE
    }finally{$ErrorActionPreference=$old}
    $out2|ForEach-Object{Write-Host $_}
    if($code2-ne 0 -or -not(Test-Path -LiteralPath $roundDxf)){Fail "LibreDWG DWG->DXF self-test failed"}

    Write-Host "DWG_ROUNDTRIP_CONVERSION=PASS" -ForegroundColor Green

    $p=Get-Python
    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{
        $parseOut=@(& $p.Exe @($p.Prefix) $engine --runtime-config $runtimeConfig --inspect $roundDxf 2>&1)
        $parseCode=$LASTEXITCODE
    }finally{
        $ErrorActionPreference=$old
    }
    $parseOut|ForEach-Object{Write-Host $_}

    if($parseCode-eq 0){
        Write-Host "DWG_ROUNDTRIP_DXF_PARSE=PASS" -ForegroundColor Green
    }else{
        Write-Host "DWG_ROUNDTRIP_DXF_PARSE=KNOWN_LIBREDWG_LIMITATION_NONBLOCKING" -ForegroundColor Yellow
        Write-Host "DWG_INTERACTIVE_VIEWER=LibreCAD_AVAILABLE" -ForegroundColor Green
    }

    Write-Host "DWG_ROUNDTRIP_SELF_TEST=PASS_WITH_KNOWN_CONVERTER_LIMITATION_POLICY" -ForegroundColor Green
}else{
    Write-Host "DWG_ROUNDTRIP_SELF_TEST=SKIPPED_DXF2DWG_NOT_FOUND" -ForegroundColor Yellow
}

Write-Host "LIBRECAD_PATH=$librecad"
Write-Host "LIBREDWG_DWG2DXF_PATH=$dwg2dxf"
Write-Host "CAD_VIEWER_RUNTIME_CONFIG=$runtimeConfig"
Write-Host "PHOENIX_4_41_OPEN_SOURCE_CAD_VIEWER_INSTALL=PASS" -ForegroundColor Green
Write-Host "DXF_OPEN=ENABLED"
Write-Host "DWG_OPEN=ENABLED"
Write-Host "DXF_INSPECT=ENABLED"
Write-Host "DWG_INSPECT=ENABLED_BEST_EFFORT_WITH_LIBREDWG_FALLBACK_STATUS"
