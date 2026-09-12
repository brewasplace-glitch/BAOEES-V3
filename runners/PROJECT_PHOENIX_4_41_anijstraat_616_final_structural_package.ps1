[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$SourcePdf = "",
    [string]$OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message){ throw $Message }

function Get-Python {
    if(Get-Command py.exe -ErrorAction SilentlyContinue){ return @{Exe="py.exe";Prefix=@("-3")} }
    if(Get-Command python.exe -ErrorAction SilentlyContinue){ return @{Exe="python.exe";Prefix=@()} }
    Fail "Python 3 not found"
}

function Invoke-Python {
    param([Parameter(Mandatory=$true)][string[]]$PyArgs)
    $p=Get-Python
    $old=$ErrorActionPreference
    $ErrorActionPreference="Continue"
    try{$out=@(& $p.Exe @($p.Prefix) @PyArgs 2>&1);$code=$LASTEXITCODE}finally{$ErrorActionPreference=$old}
    $out|ForEach-Object{Write-Host $_}
    if($code-ne 0){Fail "Python failed with exit code ${code}"}
}

function Ensure-FinalRuntime {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\final_structural_package_v1"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null
    $markers=@(
        (Join-Path $deps "docx\__init__.py"),
        (Join-Path $deps "reportlab\__init__.py"),
        (Join-Path $deps "pypdf\__init__.py")
    )
    $missing=$false
    foreach($m in $markers){if(-not(Test-Path -LiteralPath $m -PathType Leaf)){$missing=$true}}
    if($missing){
        Write-Host "FINAL_STRUCTURAL_PACKAGE_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference
        $ErrorActionPreference="Continue"
        try{
            $out=@(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps `
                "python-docx==1.2.0" "reportlab==5.0.1" "pypdf==5.9.0" 2>&1)
            $code=$LASTEXITCODE
        }finally{$ErrorActionPreference=$old}
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "Final package runtime installation failed"}
    }else{
        Write-Host "FINAL_STRUCTURAL_PACKAGE_RUNTIME=EXISTING"
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
    $OutputRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_FINAL_STRUCTURAL_PACKAGE_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot|Out-Null

$deps=Ensure-FinalRuntime
$qaDeps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\structural_qa_bim_v1"
$verify3dDeps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\structural_3d_report_verify_v1"
$env:PYTHONPATH="$RepoRoot;$deps;$qaDeps;$verify3dDeps"

$designEngine=Join-Path $RepoRoot "phoenix\structural_design_consolidation\engine.py"
$solverEngine=Join-Path $RepoRoot "phoenix\structural_solver_verification\engine.py"
$reportEngine=Join-Path $RepoRoot "phoenix\structural_3d_report\engine.py"
$qaEngine=Join-Path $RepoRoot "phoenix\structural_qa_bim\engine.py"
$engine=Join-Path $RepoRoot "phoenix\structural_final_package\engine.py"

$designRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_STRUCTURAL_DESIGN_DRAWINGS_*" -Files @("structural_design_consolidation.json")
if(-not $designRoot){Fail "Verified design evidence not found"}
Invoke-Python -PyArgs @($designEngine,"--verify-output",(Join-Path $designRoot "structural_design_consolidation.json"))
Write-Host "DESIGN_EVIDENCE=VERIFIED" -ForegroundColor Green

$solverRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION_*" -Files @("solver_element_verification.json")
if(-not $solverRoot){Fail "Verified solver evidence not found"}
Invoke-Python -PyArgs @($solverEngine,"--verify-output",(Join-Path $solverRoot "solver_element_verification.json"))
Write-Host "SOLVER_EVIDENCE=VERIFIED" -ForegroundColor Green

$reportRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_3D_STRUCTURAL_MODEL_REPORT_*" -Files @("structural_3d_report_summary.json")
if(-not $reportRoot){Fail "Verified 3D/report evidence not found"}
Invoke-Python -PyArgs @($reportEngine,"--verify-output",(Join-Path $reportRoot "structural_3d_report_summary.json"))
Write-Host "3D_REPORT_EVIDENCE=VERIFIED" -ForegroundColor Green

$qaRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_STRUCTURAL_QA_BIM_*" -Files @(
    "structural_QA_BIM_summary.json",
    "structural_QA_release_gate.json"
)
if(-not $qaRoot){Fail "Verified QA/BIM evidence not found"}
Invoke-Python -PyArgs @($qaEngine,"--verify-output",(Join-Path $qaRoot "structural_QA_BIM_summary.json"))
Write-Host "QA_BIM_EVIDENCE=VERIFIED" -ForegroundColor Green

Invoke-Python -PyArgs @(
    $engine,
    "--design-root",$designRoot,
    "--solver-root",$solverRoot,
    "--report3d-root",$reportRoot,
    "--qa-root",$qaRoot,
    "--source-pdf",$SourcePdf,
    "--output",$OutputRoot
)

Invoke-Python -PyArgs @($engine,"--verify-output",(Join-Path $OutputRoot "final_structural_package_summary.json"))

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_RELEASE_HOLD_CLOSURE_FINAL_STRUCTURAL_PACKAGE=PASS" -ForegroundColor Green
Write-Host "RELEASE_DECISION=HOLD" -ForegroundColor Yellow
Write-Host "NEXT_STAGE=PHOENIX_4.41_EXTERNAL_RELEASE_EVIDENCE_INGESTION_AND_FINAL_APPROVAL_GATE"
Write-Host "OUTPUT=$OutputRoot"
