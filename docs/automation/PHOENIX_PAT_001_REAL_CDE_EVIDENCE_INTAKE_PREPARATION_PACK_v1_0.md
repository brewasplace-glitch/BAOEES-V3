# PROJECT PHOENIX — PHOENIX-PAT-001 Real C/D/E Evidence Intake Preparation Pack v1.0

## Doel

Dit pack bereidt de echte resterende R9.5 evidence-intake voor PHOENIX-PAT-001 voor.

Het bouwt geen nieuw R9.5-framework en wijzigt de structural chain niet. De bestaande autoriteit blijft:

1. R9.5.2.9 — combined intake normalization;
2. Package E R9.5.2.5 — independent alternate-path evidence validator;
3. Package C R9.5.2.6 — seismic scope & criteria validator;
4. Package D R9.5.2.7 — weak-storey professional review validator;
5. R9.5.2.8 — remaining-evidence gate + controlled R9.5 requalification.

## Wat automatisch mag

- bestaande Phoenix evidence inventariseren;
- bestaande projectbestanden en R9.5.2.4-status vinden;
- bestaande niet-lege menselijke/professionele waarden behouden;
- het gecombineerde intakebestand op de workspace-locatie klaarzetten;
- een exact gap-register en reviewchecklist genereren;
- een supplied Package-E source file met SHA-256 controleren.

## Wat niet automatisch mag

- seismic applicability beslissen;
- seismische grenswaarden verzinnen;
- weak-storey screening professioneel accepteren;
- reviewer-identiteit of reviewstatus fabriceren;
- interne alternate-path screening als independent evidence promoten;
- code compliance of professional approval claimen;
- Production of FOR-CONSTRUCTION vrijgeven.

## Project

`PHOENIX-PAT-001`

## Vereiste baseline

`cf5f86dd97280f9dea38a672c63e78a30a9d22f4`

## Gegenereerde projectbestanden

Onder:

`projects/runtime/PHOENIX-PAT-001/inputs/structural/`

worden voorbereid:

- `r9_5_remaining_evidence_combined_intake_REQUIRED.json`
- `r9_5_remaining_evidence_CDE_GAP_REGISTER.json`
- `r9_5_remaining_evidence_CDE_EXISTING_EVIDENCE_CONTEXT.json`
- `r9_5_remaining_evidence_CDE_PROFESSIONAL_REVIEW_CHECKLIST.md`

Het combined-intakebestand is de echte input voor de al geïnstalleerde R9.5.2.9-laag.

## Installatiekwaliteit

De installer gebruikt baseline/branch/remote preflight, Python syntax, dedicated tests,
R9.5.2.2 legacy compatibility, volledige suite-aware regressie, root smoke test,
test-output cleanup, git diff check, safety assertions, secret scan, scopecontrole,
commit/push en fail-closed rollback.

PAT-001 wordt niet opnieuw uitgevoerd door dit preparation pack.
