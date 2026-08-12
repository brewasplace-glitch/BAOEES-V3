# PROJECT PHOENIX R9.5.2.5 — Package E Alternate-Path Independent Evidence

Baseline: `7938997d629410eca900084bf4bac08f8e630a42`

R9.5.2.4 has qualified 5/9 R9.5 checks and resolved Packages A and B. Package E remains open because the
existing R9.3 alternate-path result is screening only; it is not independent redistributed member-removal
evidence.

R9.5.2.5 installs a dedicated evidence intake, SHA-256 validation, independence attestation, R9.5 merge and
one-pass requalification path for Package E.

On the first PAT after installation, if no Package E input exists, Phoenix creates:

`projects/runtime/PHOENIX-PAT-001/inputs/structural/package_e_alternate_path_independent_evidence_REQUIRED.json`

Phoenix does not manufacture the independent evidence or its review. To qualify Package E, the intake must
contain actual repository-relative independent engineering evidence, a matching SHA-256, a traceable primary
source record, a traceable minimum residual-capacity proxy criterion, `alternate_path_verified=true` only
when supported, review status `REVIEWED`, a review reference, and an independence attestation.

Safety invariants:
- R9.3 screening is not promoted to independent redistributed analysis.
- Phoenix-generated evidence cannot satisfy independence.
- `NOT_APPLICABLE` does not auto-waive v8.6.
- No automatic independent review, professional review, compliance or approval claim.
- No automatic seismic scope decision.
- Professional structural review remains required.
- Production / for-construction release remains `LOCKED`.

Expected first PAT after installation: 5/9 remains qualified and one external independent-evidence item is
requested. After genuinely valid Package E evidence is supplied, the Package E check can requalify to 6/9,
leaving the postponed Packages C and D unresolved.
