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
    if (Get-Command py.exe -ErrorAction SilentlyContinue) { return @{Exe="py.exe"; Prefix=@("-3")} }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) { return @{Exe="python.exe"; Prefix=@()} }
    Fail "Python 3 not found"
}

function Invoke-Python {
    param([Parameter(Mandatory=$true)][string[]]$PyArgs)
    $p = Get-Python
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = @(& $p.Exe @($p.Prefix) @PyArgs 2>&1)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
    }
    $out | ForEach-Object { Write-Host $_ }
    if ($code -ne 0) { Fail "Python failed with exit code ${code}" }
}

function Ensure-OpenSeesPy {
    $deps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\openseespy_3_8_0_0"
    New-Item -ItemType Directory -Force -Path $deps | Out-Null
    $marker = Join-Path $deps "openseespy\opensees.py"
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
        Write-Host "OPENSEESPY_RUNTIME=MISSING_INSTALL_LOCAL"
        $p = Get-Python
        $old = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $out = @(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps "openseespy==3.8.0.0" 2>&1)
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $old
        }
        $out | ForEach-Object { Write-Host $_ }
        if ($code -ne 0) { Fail "OpenSeesPy isolated runtime installation failed" }
    } else {
        Write-Host "OPENSEESPY_RUNTIME=EXISTING"
    }
    return $deps
}

function Ensure-PyNite {
    $deps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pynitefea_3_0_0"
    New-Item -ItemType Directory -Force -Path $deps | Out-Null
    $marker = Join-Path $deps "Pynite\__init__.py"
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
        Write-Host "PYNITE_RUNTIME=MISSING_INSTALL_LOCAL"
        $p = Get-Python
        $old = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $out = @(& $p.Exe @($p.Prefix) -m pip install --disable-pip-version-check --no-input --target $deps "PyNiteFEA==3.0.0" 2>&1)
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $old
        }
        $out | ForEach-Object { Write-Host $_ }
        if ($code -ne 0) { Fail "PyNiteFEA isolated runtime installation failed" }
    } else {
        Write-Host "PYNITE_RUNTIME=EXISTING"
    }
    return $deps
}

function Find-CalculiX {
    foreach ($name in @("ccx_dynamic.exe","ccx.exe","ccx_2.23.exe","ccx_2.22.exe")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }

    $roots = @($RepoRoot, (Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX"))
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        $hit = Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^ccx.*\.exe$' } |
            Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return ""
}

if (-not $SourcePdf) { Fail "SourcePdf is required" }
if (-not (Test-Path -LiteralPath $SourcePdf -PathType Leaf)) { Fail "Source PDF not found: $SourcePdf" }

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot = Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$pdfDeps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pdf_gap_v1"
$opsDeps = Ensure-OpenSeesPy
$pyniteDeps = Ensure-PyNite
$p = Get-Python
$pyver = @(& $p.Exe @($p.Prefix) -c "import sys,platform; print(sys.version.split()[0] + '|' + platform.architecture()[0])" 2>&1)
if ($LASTEXITCODE -ne 0) { Fail "Unable to determine Python runtime" }
Write-Host "PYTHON_RUNTIME=$($pyver -join '')"
$env:PYTHONPATH = "$RepoRoot;$pdfDeps;$opsDeps;$pyniteDeps"

$DerivationRunner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_anijstraat_616_structural_derivation_load.ps1"
$SolverEngine = Join-Path $RepoRoot "phoenix\structural_solver_verification\engine.py"
$SolverConfig = Join-Path $RepoRoot "configs\phoenix\anijstraat_616_solver_element_verification_v1.json"
foreach ($f in @($DerivationRunner,$SolverEngine,$SolverConfig)) {
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { Fail "Required file missing: $f" }
}

$DerivationOut = Join-Path $OutputRoot "_prerequisite_derivation"
& powershell -NoProfile -ExecutionPolicy Bypass -File $DerivationRunner -RepoRoot $RepoRoot -SourcePdf $SourcePdf -OutputRoot $DerivationOut
if ($LASTEXITCODE -ne 0) { Fail "Prerequisite structural derivation/load rerun failed" }

$DerivationJson = Join-Path $DerivationOut "structural_derivation_load_model.json"
$ccx = Find-CalculiX
if ($ccx) {
    Write-Host "CALCULIX_DISCOVERED=$ccx"
} else {
    Write-Host "CALCULIX_DISCOVERED=NO"
}

$args = @(
    $SolverEngine,
    "--derivation",$DerivationJson,
    "--config",$SolverConfig,
    "--output",$OutputRoot
)
if ($ccx) { $args += @("--ccx-exe",$ccx) }

Invoke-Python -PyArgs $args
Invoke-Python -PyArgs @($SolverEngine,"--verify-output",(Join-Path $OutputRoot "solver_element_verification.json"))

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION=PASS" -ForegroundColor Green
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS"
Write-Host "OUTPUT=$OutputRoot"
