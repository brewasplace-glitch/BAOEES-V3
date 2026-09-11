[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$SourcePdf = "",
    [string]$OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) { throw $Message }

function Find-Python {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        return @{ Exe = "py.exe"; Prefix = @("-3") }
    }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) {
        return @{ Exe = "python.exe"; Prefix = @() }
    }
    Fail "Python 3 not found"
}

function Invoke-Python {
    param(
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$PyArgs,
        [switch]$AllowFailure
    )
    $p = Find-Python
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = @(& $p.Exe @($p.Prefix) @PyArgs 2>&1)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
    }
    $out | ForEach-Object { Write-Host $_ }
    if (-not $AllowFailure -and $code -ne 0) {
        Fail "Python failed with exit code ${code}"
    }
    return [int]$code
}

$Downloads = Join-Path $env:USERPROFILE "Downloads"
if (-not $SourcePdf) {
    $full = Get-ChildItem -LiteralPath $Downloads -File -Filter "*.pdf" |
        Where-Object { $_.Name -match "plafond.*Anijstraat.*616|Huis.*Anijstraat.*616" } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $full) {
        $full = Get-ChildItem -LiteralPath $Downloads -File -Filter "*.pdf" |
            Where-Object { $_.Name -match "Anijstraat.*616" -and $_.Name -notmatch "Blad_15|Situatie" } |
            Sort-Object Length -Descending | Select-Object -First 1
    }
    if (-not $full) { Fail "Complete Anijstraat #616 design PDF not found in Downloads" }
    $SourcePdf = $full.FullName
}
if (-not (Test-Path -LiteralPath $SourcePdf -PathType Leaf)) { Fail "Source PDF not found: $SourcePdf" }

if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMddTHHmmss"
    $OutputRoot = Join-Path $Downloads "PHOENIX_ANIJSTRAAT_616_STRUCTURAL_INPUT_GAP_$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$Deps = Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pdf_gap_v1"
$env:PYTHONPATH = "$RepoRoot;$Deps"

$probe = Invoke-Python -AllowFailure -PyArgs @("-c", "import importlib.util,sys;sys.exit(0 if (importlib.util.find_spec('pdfplumber') or importlib.util.find_spec('pypdf')) else 7)")
if ($probe -ne 0) {
    Write-Host "PDF_RUNTIME_DEPS=MISSING_INSTALL_LOCAL_RUNTIME" -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $Deps | Out-Null
    Invoke-Python -PyArgs @("-m","pip","install","--disable-pip-version-check","--target",$Deps,"pdfplumber>=0.11.10,<0.12","pypdf>=5,<7")
    $env:PYTHONPATH = "$RepoRoot;$Deps"
}

$Analyzer = Join-Path $RepoRoot "phoenix\structural_input_gap\analyzer.py"
$Config = Join-Path $RepoRoot "configs\phoenix\anijstraat_616_structural_input_gap_v1.json"

Invoke-Python -PyArgs @($Analyzer,"--pdf",$SourcePdf,"--config",$Config,"--output",$OutputRoot)
Invoke-Python -PyArgs @($Analyzer,"--verify-output",(Join-Path $OutputRoot "structural_input_gap_analysis.json"))

Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_STRUCTURAL_INPUT_GAP=PASS" -ForegroundColor Green
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_DERIVATION_AND_LOAD_MODEL"
Write-Host "OUTPUT=$OutputRoot"
