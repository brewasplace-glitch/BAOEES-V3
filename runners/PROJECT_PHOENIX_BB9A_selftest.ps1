param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

python -m unittest tests.build_system.test_phoenix_build_system -v
if ($LASTEXITCODE -ne 0) {
    throw "BB9A unit tests failed."
}

powershell -ExecutionPolicy Bypass -File `
    ".\runners\PROJECT_PHOENIX_BB9A_knowledge_index.ps1" `
    -RepoRoot $RepoRoot

if ($LASTEXITCODE -ne 0) {
    throw "BB9A index self-test failed."
}

Write-Host "Phoenix BB9A self-test: PASSED" -ForegroundColor Green
