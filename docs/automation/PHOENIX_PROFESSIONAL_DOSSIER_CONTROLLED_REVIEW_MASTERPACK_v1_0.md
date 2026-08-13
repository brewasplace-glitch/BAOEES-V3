# PROJECT PHOENIX — Professional Dossier & Controlled Review Masterpack v1.0

## Baseline

`6f6c0e749742170299766a9b97db4aa5dcba9b71`

## Position in the workflow

Phoenix / SCIA calculation
→ `CALCULATED_UNVERIFIED`
→ Structural Independent Verification
→ `TECHNICALLY_VERIFIED` or `TECHNICALLY_CROSS_VERIFIED`
→ **Professional Dossier & Controlled Review**
→ human reviewer return
→ controlled record of reviewer decision.

## What the reviewer receives

The plan supports the standard dossier set:

1. structural basis PDF;
2. structural calculation PDF;
3. editable DOCX;
4. SCIA `.ESA`;
5. loads and combinations;
6. Phoenix QA/QC;
7. SCIA↔CalculiX verification;
8. analytical spot checks;
9. evidence manifest;
10. open review points;
11. reviewer return form.

All submitted files are copied into an immutable review dossier and hashed.

## Reviewer decisions

- `REVIEWED_WITHOUT_CHANGES`
- `REVIEWED_WITH_CHANGES`
- `RECALCULATION_REQUIRED`
- `REJECTED`

`REVIEWED_WITH_CHANGES` requires at least one actual content-changed replacement file.
Phoenix compares submitted and returned SHA-256 values and records changed roles.

## Hard boundary

A professional review return is human-authored evidence. Phoenix may validate:
- identity fields;
- dossier identity;
- file presence;
- SHA-256 differences;
- decision completeness.

Phoenix may not automatically turn that return into:
- a code-compliance claim;
- Production release;
- FOR-CONSTRUCTION release.

Those gates remain separate and locked.
