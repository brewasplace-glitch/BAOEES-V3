param([string]$Repository="C:\PROJECT-PHOENIX",[string]$EvidenceRoot="C:\PROJECT-PHOENIX\evidence\moskee_bunschoten")
Set-Location $Repository
python runners\PROJECT_PHOENIX_professional_evidence_closure_engine_v6_3_0.py --repository $Repository --project configs\projects\moskee_bunschoten_professional_evidence_v6_3_0.json --output outputs\runtime\professional_evidence_closure_v6_3_0 --evidence-root $EvidenceRoot
if($LASTEXITCODE-ne 0){throw "Evidence closure failed: $LASTEXITCODE"}
