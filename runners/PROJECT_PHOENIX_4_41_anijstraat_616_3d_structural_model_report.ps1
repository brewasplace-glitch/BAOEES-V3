[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$SourcePdf = "",
    [string]$OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    throw $Message
}

function Get-Python {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        return @{ Exe = "py.exe"; Prefix = @("-3") }
    }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) {
        return @{ Exe = "python.exe"; Prefix = @() }
    }
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
    }
    finally {
        $ErrorActionPreference = $old
    }

    $out | ForEach-Object { Write-Host $_ }
    if ($code -ne 0) {
        Fail "Python failed with exit code ${code}"
    }
}

function Ensure-ReportRuntime {
    $deps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\structural_3d_report_v1"
    New-Item -ItemType Directory -Force -Path $deps | Out-Null

    $markers = @(
        (Join-Path $deps "trimesh\__init__.py"),
        (Join-Path $deps "docx\__init__.py"),
        (Join-Path $deps "reportlab\__init__.py"),
        (Join-Path $deps "PIL\__init__.py")
    )

    $missing = $false
    foreach ($marker in $markers) {
        if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
            $missing = $true
        }
    }

    if ($missing) {
        Write-Host "STRUCTURAL_3D_REPORT_RUNTIME=MISSING_INSTALL_LOCAL"

        $p = Get-Python
        $old = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $out = @(
                & $p.Exe @($p.Prefix) -m pip install `
                    --disable-pip-version-check `
                    --no-input `
                    --target $deps `
                    "trimesh==5.1.0" `
                    "python-docx==1.2.0" `
                    "reportlab==5.0.1" `
                    "Pillow==12.3.0" 2>&1
            )
            $code = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $old
        }

        $out | ForEach-Object { Write-Host $_ }
        if ($code -ne 0) {
            Fail "3D/report isolated runtime installation failed"
        }
    }
    else {
        Write-Host "STRUCTURAL_3D_REPORT_RUNTIME=EXISTING"
    }

    return $deps
}

function Find-LatestFolder {
    param(
        [Parameter(Mandatory=$true)][string]$Pattern,
        [Parameter(Mandatory=$true)][string[]]$Files
    )

    $downloads = Join-Path $env:USERPROFILE "Downloads"
    $dirs = @(
        Get-ChildItem -LiteralPath $downloads `
            -Directory `
            -Filter $Pattern `
            -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    )

    foreach ($dir in $dirs) {
        $ok = $true
        foreach ($file in $Files) {
            if (-not (Test-Path -LiteralPath (Join-Path $dir.FullName $file) -PathType Leaf)) {
                $ok = $false
            }
        }
        if ($ok) {
            return $dir.FullName
        }
    }

    return ""
}

if (-not $SourcePdf) {
    Fail "SourcePdf required"
}
if (-not (Test-Path -LiteralPath $SourcePdf -PathType Leaf)) {
    Fail "Source PDF missing: $SourcePdf"
}

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot = Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_3D_STRUCTURAL_MODEL_REPORT_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

Write-Host "RUNNER_LINE_ENDING_FIX=ACTIVE" -ForegroundColor Green

$deps = Ensure-ReportRuntime
$pdfDeps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pdf_gap_v1"
$env:PYTHONPATH = "$RepoRoot;$deps;$pdfDeps"

$designEngine = Join-Path $RepoRoot "phoenix\structural_design_consolidation\engine.py"
$designRunner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_anijstraat_616_structural_design_consolidation.ps1"
$solverEngine = Join-Path $RepoRoot "phoenix\structural_solver_verification\engine.py"
$solverRunner = Join-Path $RepoRoot "runners\PROJECT_PHOENIX_4_41_anijstraat_616_solver_element_verification.ps1"
$engine = Join-Path $RepoRoot "phoenix\structural_3d_report\engine.py"
$config = Join-Path $RepoRoot "configs\phoenix\anijstraat_616_3d_structural_report_v1.json"

foreach ($required in @($designEngine,$designRunner,$solverEngine,$solverRunner,$engine,$config)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        Fail "Required Phoenix file missing: $required"
    }
}

$designRoot = Find-LatestFolder `
    -Pattern "PHOENIX_ANIJSTRAAT_616_STRUCTURAL_DESIGN_DRAWINGS_*" `
    -Files @("structural_design_consolidation.json")

if (-not $designRoot) {
    Write-Host "DESIGN_EVIDENCE_SOURCE=REGENERATE"
    $designRoot = Join-Path $OutputRoot "_design_rerun"

    & powershell -NoProfile -ExecutionPolicy Bypass `
        -File $designRunner `
        -RepoRoot $RepoRoot `
        -SourcePdf $SourcePdf `
        -OutputRoot $designRoot

    if ($LASTEXITCODE -ne 0) {
        Fail "Design evidence regeneration failed"
    }
}
else {
    Write-Host "DESIGN_EVIDENCE_CANDIDATE=$designRoot"
}

$designJson = Join-Path $designRoot "structural_design_consolidation.json"
Invoke-Python -PyArgs @(
    $designEngine,
    "--verify-output",
    $designJson
)
Write-Host "DESIGN_EVIDENCE=VERIFIED" -ForegroundColor Green

$solverRoot = Find-LatestFolder `
    -Pattern "PHOENIX_ANIJSTRAAT_616_SOLVER_ELEMENT_VERIFICATION_*" `
    -Files @(
        "solver_element_verification.json",
        "_prerequisite_derivation\structural_derivation_load_model.json"
    )

if (-not $solverRoot) {
    Write-Host "SOLVER_EVIDENCE_SOURCE=REGENERATE"
    $solverRoot = Join-Path $OutputRoot "_solver_rerun"

    & powershell -NoProfile -ExecutionPolicy Bypass `
        -File $solverRunner `
        -RepoRoot $RepoRoot `
        -SourcePdf $SourcePdf `
        -OutputRoot $solverRoot

    if ($LASTEXITCODE -ne 0) {
        Fail "Solver evidence regeneration failed"
    }
}
else {
    Write-Host "SOLVER_EVIDENCE_CANDIDATE=$solverRoot"
}

$solverJson = Join-Path $solverRoot "solver_element_verification.json"
$derivJson = Join-Path $solverRoot "_prerequisite_derivation\structural_derivation_load_model.json"

Invoke-Python -PyArgs @(
    $solverEngine,
    "--verify-output",
    $solverJson
)
Write-Host "SOLVER_EVIDENCE=VERIFIED" -ForegroundColor Green

Invoke-Python -PyArgs @(
    $engine,
    "--design-json",$designJson,
    "--solver-json",$solverJson,
    "--derivation-json",$derivJson,
    "--source-pdf",$SourcePdf,
    "--config",$config,
    "--output",$OutputRoot
)

Invoke-Python -PyArgs @(
    $engine,
    "--verify-output",
    (Join-Path $OutputRoot "structural_3d_report_summary.json")
)

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_3D_STRUCTURAL_MODEL_CALCULATION_REPORT=PASS" -ForegroundColor Green
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_QA_RELEASE_GATE_AND_BIM_INTEGRATION"
Write-Host "OUTPUT=$OutputRoot"
