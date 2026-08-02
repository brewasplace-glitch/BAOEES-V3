$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Repo "runners\PROJECT_PHOENIX_OFFICIAL_START_v3_0_1.py"

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Phoenix Official Start v3.0.2 runner ontbreekt: $Runner"
}

python $Runner
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Official Start v3.0.2 kon niet worden geopend."
}
