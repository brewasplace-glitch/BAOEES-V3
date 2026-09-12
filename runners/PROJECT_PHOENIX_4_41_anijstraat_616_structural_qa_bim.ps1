[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$SourcePdf = "",
    [string]$OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) { throw $Message }

function Get-Python {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) { return @{Exe="py.exe";Prefix=@("-3")} }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) { return @{Exe="python.exe";Prefix=@()} }
    Fail "Python 3 not found"
}

function Invoke-Python {
    param([Parameter(Mandatory=$true)][string[]]$PyArgs)
    $p=Get-Python
    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try {
        $out=@(& $p.Exe @($p.Prefix) @PyArgs 2>&1)
        $code=$LASTEXITCODE
    }
    finally { $ErrorActionPreference=$old }
    $out|ForEach-Object{Write-Host $_}
    if($code-ne 0){Fail "Python failed with exit code ${code}"}
}

function Ensure-BimRuntime {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\structural_qa_bim_v1"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null
    $markers=@(
        (Join-Path $deps "ifcopenshell\__init__.py"),
        (Join-Path $deps "ifctester\__init__.py")
    )
    $missing=$false
    foreach($m in $markers){if(-not(Test-Path -LiteralPath $m -PathType Leaf)){$missing=$true}}
    if($missing){
        Write-Host "STRUCTURAL_QA_BIM_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference
        $ErrorActionPreference="Continue"
        try{
            $out=@(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps "ifcopenshell==0.8.5" "ifctester==0.8.5" 2>&1)
            $code=$LASTEXITCODE
        }finally{$ErrorActionPreference=$old}
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "IFC/IDS isolated runtime installation failed"}
    }else{
        Write-Host "STRUCTURAL_QA_BIM_RUNTIME=EXISTING"
    }
    return $deps
}

function Ensure-3DVerificationRuntime {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\structural_3d_report_verify_v1"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null

    $markers=@(
        (Join-Path $deps "trimesh\__init__.py"),
        (Join-Path $deps "docx\__init__.py"),
        (Join-Path $deps "pypdf\__init__.py")
    )

    $missing=$false
    foreach($m in $markers){
        if(-not(Test-Path -LiteralPath $m -PathType Leaf)){$missing=$true}
    }

    if($missing){
        Write-Host "STRUCTURAL_3D_VERIFY_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference
        $ErrorActionPreference="Continue"
        try{
            $out=@(
                & $p.Exe @($p.Prefix) -m pip install `
                    --disable-pip-version-check `
                    --no-input `
                    --target $deps `
                    "trimesh==5.1.0" `
                    "python-docx==1.2.0" `
                    "pypdf==5.9.0" 2>&1
            )
            $code=$LASTEXITCODE
        }finally{
            $ErrorActionPreference=$old
        }
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "3D verification compatibility runtime installation failed"}
    }else{
        Write-Host "STRUCTURAL_3D_VERIFY_RUNTIME=EXISTING"
    }

    return $deps
}

function Find-LatestFolder {
    param(
        [Parameter(Mandatory=$true)][string]$Pattern,
        [Parameter(Mandatory=$true)][string[]]$Files
    )
    $downloads=Join-Path $env:USERPROFILE "Downloads"
    $dirs=@(Get-ChildItem -LiteralPath $downloads -Directory -Filter $Pattern -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    foreach($d in $dirs){
        $ok=$true
        foreach($f in $Files){
            if(-not(Test-Path -LiteralPath (Join-Path $d.FullName $f) -PathType Leaf)){$ok=$false}
        }
        if($ok){return $d.FullName}
    }
    return ""
}

if(-not $SourcePdf){Fail "SourcePdf required"}
if(-not(Test-Path -LiteralPath $SourcePdf -PathType Leaf)){Fail "Source PDF missing: $SourcePdf"}

if(-not $OutputRoot){
    $stamp=Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_STRUCTURAL_QA_BIM_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot|Out-Null

$deps=Ensure-BimRuntime
$verify3dDeps=Ensure-3DVerificationRuntime
$env:PYTHONPATH="$RepoRoot;$deps;$verify3dDeps"
Write-Host "CROSS_STAGE_RUNTIME_BRIDGE=QA_BIM+3D_VERIFY" -ForegroundColor Green

Invoke-Python -PyArgs @(
    "-c",
    "import ifcopenshell,ifctester,trimesh,docx,pypdf; print('CROSS_STAGE_PYTHON_IMPORTS=PASS')"
)

$designEngine=Join-Path $RepoRoot "phoenix\structural_design_consolidation\engine.py"
$solverEngine=Join-Path $RepoRoot "phoenix\structural_solver_verification\engine.py"
$reportEngine=Join-Path $RepoRoot "phoenix\structural_3d_report\engine.py"
$engine=Join-Path $RepoRoot "phoenix\structural_qa_bim\engine.py"

$designRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_STRUCTURAL_DESIGN_DRAWINGS_*" -Files @("structural_design_consolidation.json")
if(-not $designRoot){Fail "Verified design evidence folder not found in Downloads"}
$designJson=Join-Path $designRoot "structural_design_consolidation.json"
Invoke-Python -PyArgs @($designEngine,"--verify-output",$designJson)
Write-Host "DESIGN_EVIDENCE=VERIFIED" -ForegroundColor Green

$solverRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION_*" -Files @("solver_element_verification.json")
if(-not $solverRoot){Fail "Verified solver evidence folder not found in Downloads"}
$solverJson=Join-Path $solverRoot "solver_element_verification.json"
Invoke-Python -PyArgs @($solverEngine,"--verify-output",$solverJson)
Write-Host "SOLVER_EVIDENCE=VERIFIED" -ForegroundColor Green

$reportRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_3D_STRUCTURAL_MODEL_REPORT_*" -Files @(
    "structural_3d_report_summary.json",
    "3d_structural_model_metadata.json"
)
if(-not $reportRoot){Fail "Verified 3D/report evidence folder not found in Downloads"}
$reportJson=Join-Path $reportRoot "structural_3d_report_summary.json"
$modelMetadata=Join-Path $reportRoot "3d_structural_model_metadata.json"
Invoke-Python -PyArgs @($reportEngine,"--verify-output",$reportJson)
Write-Host "3D_REPORT_EVIDENCE=VERIFIED" -ForegroundColor Green

Invoke-Python -PyArgs @(
    $engine,
    "--design-json",$designJson,
    "--solver-json",$solverJson,
    "--report3d-json",$reportJson,
    "--model-metadata",$modelMetadata,
    "--source-pdf",$SourcePdf,
    "--output",$OutputRoot
)
Invoke-Python -PyArgs @($engine,"--verify-output",(Join-Path $OutputRoot "structural_QA_BIM_summary.json"))

$freecad=(Get-Command FreeCADCmd.exe -ErrorAction SilentlyContinue)
if($freecad){
    Write-Host "FREECAD_FALLBACK_DISCOVERED=$($freecad.Source)"
}else{
    Write-Host "FREECAD_FALLBACK_DISCOVERED=NO_NONBLOCKING"
}

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_STRUCTURAL_QA_RELEASE_GATE_BIM=PASS" -ForegroundColor Green
Write-Host "RELEASE_DECISION=HOLD" -ForegroundColor Yellow
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_RELEASE_HOLD_CLOSURE_AND_FINAL_STRUCTURAL_PACKAGE"
Write-Host "OUTPUT=$OutputRoot"
