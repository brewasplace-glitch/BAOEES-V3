# PROJECT PHOENIX R9.5.2 — Stability Design-Basis Decision Dossier & Evidence Intake Masterpack v1.0

Baseline: `566d458192c079793dc3fa5d964091f4b2b48064`

## Doel
R9.5.2 zet de door R9.5.1 gegenereerde projectspecifieke stability scaffold om in:
1. een formeel decision dossier;
2. een persistent evidence-intake bestand;
3. vijf geconsolideerde bron-/reviewpakketten.

## Huidige technische status
De R9.5.1 PAT heeft bevestigd:
- technische stabiliteitsevidence: 9/9;
- aanvullende technische analyse: 0;
- R9.5/R9.4/v8.6 blijven bewust geblokkeerd op expliciete design-basis/source/review input.

## Runtime outputs
- `v8_6/r9_5_2_stability_design_basis_decision_dossier_evidence_intake.json`
- `inputs/structural/stability_design_basis_evidence_intake_REQUIRED.json`
- `inputs/structural/stability_design_basis_decision_dossier_REQUIRED.md`

Bestaande niet-lege intakewaarden worden bij een volgende PAT behouden, maar niet automatisch als gekwalificeerd gemarkeerd.

## Vijf pakketten
- PKG-A — stability methodology decision.
- PKG-B — numerical acceptance criteria.
- PKG-C — seismic scope and criteria.
- PKG-D — weak-storey screening review.
- PKG-E — alternate-path independent evidence.

## Safety
- Geen normatieve grenswaarden automatisch invullen.
- Geen seismische applicability automatisch beslissen.
- Geen project-policy automatisch goedkeuren.
- Geen professional/independent review automatisch claimen.
- R9.5, R9.4 en v8.6 blijven de qualification gates.
- Production release blijft LOCKED.
