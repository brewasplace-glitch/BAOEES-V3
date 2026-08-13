# PROJECT PHOENIX — PHOENIX-PAT-001 Full SCIA End-to-End Masterpack v1.0

## Baseline

`33ee6e420823a26eed2bfb18bbb723e3e7a2d025`

## Goal

Drive PHOENIX-PAT-001 through the real structural workflow using the already-installed
general layers:

1. SCIA Engineer 18.1 / ESA_XML live calculation;
2. Phoenix Structural Independent Verification;
3. Professional Dossier & Controlled Review packaging;
4. stop at the human professional-review gate.

The orchestration engine is generic. PAT-001 is the first real project instance.

## Important distinction

The first live SCIA run uses `LIN` as an **E2E pipeline baseline**, not as an automatic
final project analysis-scope decision.

Phoenix will not infer NEL, seismic scope, robustness criteria or other final project
analysis requirements merely from a successful LIN pipeline run.

## Fail-closed project gates

### SCIA seed

Phoenix searches only inside:

`projects/runtime/<project_id>/`

for `.ESA` candidates.

It auto-selects only one unambiguous high-confidence input/structural seed. It does not
fabricate `.ESA` files and does not automatically select working/reviewed/result artifacts.

### Technical verification

No tolerance is invented. If a complete project verification plan is not already present,
Phoenix generates:

`structural_independent_verification_plan_REQUIRED.json`

and stops after the real SCIA calculation at the verification-input gate.

### Professional dossier

If technically verified, Phoenix requires real dossier files including PDF/DOCX/.ESA and
evidence outputs. Missing files remain a dossier-input gate.

## Expected first-run outcomes

Depending on the current project evidence, the first execution may legitimately end at:

- `BLOCKED_SCIA_SEED_REQUIRED`
- `BLOCKED_SCIA_SEED_SELECTION_REQUIRED`
- `CALCULATED_UNVERIFIED_VERIFICATION_INPUT_REQUIRED`
- `TECHNICALLY_CROSS_VERIFIED_DOSSIER_INPUT_REQUIRED`
- `READY_FOR_PROFESSIONAL_REVIEW`

These are workflow states, not fabricated successes.

## Release boundary

Production and FOR-CONSTRUCTION remain LOCKED throughout this masterpack.
Professional review is never simulated.
