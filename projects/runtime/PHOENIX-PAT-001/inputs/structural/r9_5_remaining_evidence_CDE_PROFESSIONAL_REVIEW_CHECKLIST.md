# PHOENIX-PAT-001 — Real C/D/E Professional Evidence Review Checklist

Combined intake: `C:/PROJECT-PHOENIX/projects/runtime/PHOENIX-PAT-001/inputs/structural/r9_5_remaining_evidence_combined_intake_REQUIRED.json`

## Current verified Phoenix state

- Technical analysis still required: `0`
- Current R9.5 status: `BLOCKED`
- Unresolved checks: `ALTERNATE_LOAD_PATH_EVIDENCE, SOFT_STOREY_STIFFNESS_RATIO, TORSIONAL_DRIFT_RATIO, WEAK_STOREY_STRENGTH_RATIO`
- Unresolved packages: `PKG-C-SEISMIC-SCOPE-AND-CRITERIA, PKG-D-WEAK-STOREY-SCREENING-REVIEW, PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE`
- Package B traceability complete: `True`

## Package C — Seismic scope & criteria

A professional reviewer must explicitly decide seismic applicability. Phoenix must not infer it.
If APPLICABLE, each numerical criterion requires its own source record and clause/reference.

Open fields:
- `seismic_applicability_status`
- `reference_type`
- `reference`
- `source_record_id`
- `scope_review_reference`
- `professional_scope_reviewed`

## Package D — Weak-storey screening review

The R8/R9.3 weak-storey result remains a candidate screening proxy until a professional review records an explicit decision.

Open fields:
- `screening_proxy_accepted_for_candidate_gate`
- `screening_proxy_review_reference`
- `reviewer_scope`
- `review_status`

## Package E — Independent alternate-path evidence

R9.3 alternate-path screening is not independent redistributed/nonlinear alternate-path proof.
Independent engineering evidence, file integrity, review and acceptance-criterion traceability are required.

Open fields:
- `independent_engineering_evidence_reference`
- `repository_relative_source_file`
- `sha256`
- `independent_review_reference`
- `independent_review_status`
- `independently_verified_alternate_path`
- `acceptance_criterion_and_traceability`

## Release boundary

- No automatic professional approval.
- No automatic code-compliance claim.
- No automatic seismic applicability decision.
- No fabricated independent evidence.
- Production release remains `LOCKED`.
- FOR-CONSTRUCTION release remains `LOCKED`.

After genuine professional evidence is entered, rerun the normal Phoenix project/structural session.
R9.5.2.9 will normalize the intake, Packages E/C/D remain authoritative validators, and R9.5.2.8 may invoke controlled R9.5 requalification only when all three gates are truly eligible.
