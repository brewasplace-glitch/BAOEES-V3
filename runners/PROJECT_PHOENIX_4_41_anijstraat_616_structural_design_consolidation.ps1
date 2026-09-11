[CmdletBinding()]
param(
    [string]$RepoRoot="C:\PROJECT-PHOENIX",
    [string]$SourcePdf="",
    [string]$OutputRoot=""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

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
    if($code-ne 0){Fail "Python failed with exit code ${code}"}
}

function Ensure-Ezdxf {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\ezdxf_1_4_4"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null
    $marker=Join-Path $deps "ezdxf\__init__.py"
    if(-not(Test-Path -LiteralPath $marker -PathType Leaf)){
        Write-Host "EZDXF_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference;$ErrorActionPreference="Continue"
        try{
            $out=@(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps "ezdxf==1.4.4" 2>&1)
            $code=$LASTEXITCODE
        }finally{$ErrorActionPreference=$old}
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "ezdxf isolated runtime installation failed"}
    }else{
        Write-Host "EZDXF_RUNTIME=EXISTING"
    }
    return $deps
}

function Find-VerifiedSolverEvidence {
    $downloads=Join-Path $env:USERPROFILE "Downloads"
    $dirs=@(Get-ChildItem -LiteralPath $downloads -Directory -Filter "PHOENIX_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION_*" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    foreach($d in $dirs){
        $solver=Join-Path $d.FullName "solver_element_verification.json"
        $deriv=Join-Path $d.FullName "_prerequisite_derivation\structural_derivation_load_model.json"
        if((Test-Path -LiteralPath $solver -PathType Leaf)-and(Test-Path -LiteralPath $deriv -PathType Leaf)){
            return @{Solver=$solver;Derivation=$deriv;Root=$d.FullName}
        }
    }
    return $null
}

if(-not $SourcePdf){Fail "SourcePdf required"}
if(-not(Test-Path -LiteralPath $SourcePdf -PathType Leaf)){Fail "Source PDF not found: $SourcePdf"}
if(-not $OutputRoot){
    $stamp=Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_STRUCTURAL_DESIGN_DRAWINGS_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot|Out-Null

$pdfDeps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pdf_gap_v1"
$ezDeps=Ensure-Ezdxf
$env:PYTHONPATH="$RepoRoot;$pdfDeps;$ezDeps"

$solverEngine=Join-Path $RepoRoot "phoenix\structural_solver_verification\engine.py"
$solverRunner=Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_anijstraat_616_solver_element_verification.ps1"
$engine=Join-Path $RepoRoot "phoenix\structural_design_consolidation\engine.py"
$config=Join-Path $RepoRoot "configs\phoenix\anijstraat_616_structural_design_consolidation_v1.json"

$ev=Find-VerifiedSolverEvidence
if($ev){
    Write-Host "SOLVER_EVIDENCE_CANDIDATE=$($ev.Root)"
    Invoke-Python -PyArgs @($solverEngine,"--verify-output",$ev.Solver)
    $solverJson=$ev.Solver
    $derivJson=$ev.Derivation
    Write-Host "SOLVER_EVIDENCE_SOURCE=REUSED_LATEST_VERIFIED" -ForegroundColor Green
}else{
    Write-Host "SOLVER_EVIDENCE_SOURCE=REGENERATE"
    $rerun=Join-Path $OutputRoot "_solver_rerun"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $solverRunner -RepoRoot $RepoRoot -SourcePdf $SourcePdf -OutputRoot $rerun
    if($LASTEXITCODE-ne 0){Fail "Solver evidence regeneration failed"}
    $solverJson=Join-Path $rerun "solver_element_verification.json"
    $derivJson=Join-Path $rerun "_prerequisite_derivation\structural_derivation_load_model.json"
    Invoke-Python -PyArgs @($solverEngine,"--verify-output",$solverJson)
    Write-Host "SOLVER_EVIDENCE_SOURCE=REGENERATED_VERIFIED" -ForegroundColor Green
}

Invoke-Python -PyArgs @($engine,
    "--solver-json",$solverJson,
    "--derivation-json",$derivJson,
    "--source-pdf",$SourcePdf,
    "--config",$config,
    "--output",$OutputRoot
)
Invoke-Python -PyArgs @($engine,"--verify-output",(Join-Path $OutputRoot "structural_design_consolidation.json"))

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_STRUCTURAL_DESIGN_CONSOLIDATION_DRAWINGS=PASS" -ForegroundColor Green
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_3D_STRUCTURAL_MODEL_AND_CALCULATION_REPORT"
Write-Host "OUTPUT=$OutputRoot"
