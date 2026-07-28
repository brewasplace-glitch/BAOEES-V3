param(
    [string]$Repository = "C:\PROJECT-PHOENIX"
)
$ErrorActionPreference = "Stop"
$Runner = Join-Path $Repository "runners\PROJECT_PHOENIX_BB35_pilot_1_professional_evidence_intake_validation_closure_gate_v2_3_0.py"
$Output = Join-Path $Repository "outputs\runtime\bb35_professional_evidence_closure_gate\latest"
if (Test-Path -LiteralPath $Output) { Remove-Item -LiteralPath $Output -Recurse -Force }
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$Python = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $Python) {
    & $Python.Source -3 $Runner --output-dir $Output --expect-gate-operational
} else {
    & python $Runner --output-dir $Output --expect-gate-operational
}
if ($LASTEXITCODE -ne 0) { throw "Professional evidence closure gate failed." }
Start-Process (Join-Path $Output "09_professional_evidence_intake_dashboard.html")
