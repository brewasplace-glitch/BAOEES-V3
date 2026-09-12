[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$SourcePdf = "",
    [string]$EvidenceRoot = "",
    [string]$OutputRoot = ""
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
    if($code-ne 0){Fail "Python failed with exit code ${code}"}
}

function Ensure-EvidenceRuntime {
    $deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\external_release_evidence_v1"
    New-Item -ItemType Directory -Force -Path $deps|Out-Null
    $markers=@(
        (Join-Path $deps "jsonschema\__init__.py"),
        (Join-Path $deps "cryptography\__init__.py"),
        (Join-Path $deps "docx\__init__.py"),
        (Join-Path $deps "reportlab\__init__.py"),
        (Join-Path $deps "pypdf\__init__.py")
    )
    $missing=$false
    foreach($m in $markers){if(-not(Test-Path -LiteralPath $m -PathType Leaf)){$missing=$true}}
    if($missing){
        Write-Host "EXTERNAL_RELEASE_EVIDENCE_RUNTIME=MISSING_INSTALL_LOCAL"
        $p=Get-Python
        $old=$ErrorActionPreference
        $ErrorActionPreference="Continue"
        try{
            $out=@(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps `
                "jsonschema==4.26.0" "cryptography==50.0.1" `
                "python-docx==1.2.0" "reportlab==5.0.1" "pypdf==5.9.0" 2>&1)
            $code=$LASTEXITCODE
        }finally{$ErrorActionPreference=$old}
        $out|ForEach-Object{Write-Host $_}
        if($code-ne 0){Fail "External release evidence runtime installation failed"}
    }else{
        Write-Host "EXTERNAL_RELEASE_EVIDENCE_RUNTIME=EXISTING"
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
        foreach($f in $Files){if(-not(Test-Path -LiteralPath (Join-Path $d.FullName $f) -PathType Leaf)){$ok=$false}}
        if($ok){return $d.FullName}
    }
    return ""
}

if(-not $SourcePdf){Fail "SourcePdf required"}
if(-not(Test-Path -LiteralPath $SourcePdf -PathType Leaf)){Fail "Source PDF missing: $SourcePdf"}

if(-not $EvidenceRoot){
    $EvidenceRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_EXTERNAL_RELEASE_EVIDENCE"
}
if(-not $OutputRoot){
    $stamp=Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_EXTERNAL_RELEASE_EVIDENCE_GATE_$stamp"
}

New-Item -ItemType Directory -Force -Path $OutputRoot|Out-Null
$deps=Ensure-EvidenceRuntime
$env:PYTHONPATH="$RepoRoot;$deps"

$engine=Join-Path $RepoRoot "phoenix\structural_release_evidence\engine.py"
$schema=Join-Path $RepoRoot "configs\phoenix\anijstraat_616_release_evidence_submission_schema_v1.json"
$priorEngine=Join-Path $RepoRoot "phoenix\structural_final_package\engine.py"

Invoke-Python -PyArgs @("-c","import jsonschema,cryptography,docx,reportlab,pypdf; print('EVIDENCE_RUNTIME_IMPORTS=PASS')")

Invoke-Python -PyArgs @($engine,"--self-test")

Write-Host "RUNTIME_SELF_TEST=PASS" -ForegroundColor Green

Invoke-Python -PyArgs @($engine,"--bootstrap-inbox",$EvidenceRoot,"--schema",$schema)

$finalRoot=Find-LatestFolder -Pattern "PHOENIX_ANIJSTRAAT_616_FINAL_STRUCTURAL_PACKAGE_*" -Files @(
    "final_structural_package_summary.json",
    "release_hold_closure_plan.json"
)
if(-not $finalRoot){Fail "Verified prior final preliminary structural package not found"}

Invoke-Python -PyArgs @($priorEngine,"--verify-output",(Join-Path $finalRoot "final_structural_package_summary.json"))
Write-Host "PRIOR_FINAL_STRUCTURAL_PACKAGE=VERIFIED" -ForegroundColor Green

Invoke-Python -PyArgs @(
    $engine,
    "--final-package-root",$finalRoot,
    "--evidence-root",$EvidenceRoot,
    "--schema",$schema,
    "--source-pdf",$SourcePdf,
    "--output",$OutputRoot
)

Invoke-Python -PyArgs @($engine,"--verify-output",(Join-Path $OutputRoot "external_release_evidence_gate_summary.json"))

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_EXTERNAL_RELEASE_EVIDENCE_FINAL_APPROVAL_GATE=PASS" -ForegroundColor Green
Write-Host "FOR_CONSTRUCTION_RELEASE=LOCKED" -ForegroundColor Yellow
Write-Host "EVIDENCE_ROOT=$EvidenceRoot"
Write-Host "NEXT_STAGE=PHOENIX_4.41_RELEASE_EVIDENCE_PROCESSING_LOOP_AND_SIGNED_RELEASE_ACTION"
Write-Host "OUTPUT=$OutputRoot"
