param(
 [string]$Repository="C:\PROJECT-PHOENIX",
 [string]$EvidenceRoot="C:\PROJECT-PHOENIX\evidence\moskee_bunschoten",
 [string]$Output="outputs\runtime\professional_evidence_workflow_v6_4_0"
)
$ErrorActionPreference="Stop"
Set-Location $Repository
$Python=(Get-Command python.exe -CommandType Application -All -ErrorAction Stop |
 Where-Object {
  $_.Path -notmatch '\\Microsoft\\WindowsApps\\' -and
  (Test-Path -LiteralPath $_.Path -PathType Leaf)
 } | Select-Object -First 1).Path
& $Python "runners\PROJECT_PHOENIX_professional_evidence_intake_review_workflow_v6_4_0.py" `
 --repository $Repository `
 --project "configs\projects\moskee_bunschoten_evidence_workflow_v6_4_0.json" `
 --evidence-root $EvidenceRoot `
 --output $Output
if($LASTEXITCODE-ne 0){throw "Evidence workflow failed: $LASTEXITCODE"}
