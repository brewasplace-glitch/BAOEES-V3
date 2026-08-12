# PHOENIX-PAT-001 — Professional Package C/D Review Dossier

## Purpose

This dossier presents existing Phoenix technical evidence for professional review.
It does not contain a Phoenix-authored professional decision.

## Package C — Seismic scope & criteria

Reviewer action:
- explicitly decide `APPLICABLE` or `NOT_APPLICABLE`;
- provide traceable source/reference and scope-review reference;
- if APPLICABLE, provide traceable criteria for soft-storey, torsional drift and weak-storey checks.

Existing technical evidence references:
- `R9.3:SOFT_STOREY_STIFFNESS_RATIO` — located sources: `5`; existing reference flag: `True`
- `R9.3:TORSIONAL_DRIFT_RATIO` — located sources: `5`; existing reference flag: `True`
- `R9.3:WEAK_STOREY_STRENGTH_RATIO` — located sources: `5`; existing reference flag: `True`

## Package D — Weak-storey screening review

Reviewer action:
- review the existing R8/R9.3 weak-storey candidate-screening proxy;
- explicitly accept or reject it for the candidate gate;
- provide review reference and reviewer scope.

Boundary: acceptance for the candidate gate is not a code-compliance or FOR-CONSTRUCTION approval.

## Required return files

- `package_c_professional_review_RETURN_REQUIRED.json`
- `package_d_weak_storey_review_RETURN_REQUIRED.json`

Production and FOR-CONSTRUCTION remain `LOCKED`.
