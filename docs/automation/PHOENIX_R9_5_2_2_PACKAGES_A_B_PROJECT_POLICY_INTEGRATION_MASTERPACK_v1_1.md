# PROJECT PHOENIX R9.5.2.2 — Packages A+B Project Policy Integration Masterpack v1.1

Baseline: `ca9990c83cba66ec9385db65a5b8fc48424ca6a4`

## v1.1 repair
v1.0 stopped safely during preflight because the R9.5.2 builder region contained more than one
same-indentation closing parenthesis. The v1.0 patcher therefore refused to guess.

v1.1 removes that ambiguity completely:
- the pre-R9.5 hook is still anchored directly on the unique R9.5 builder call;
- the post-R9.5.2 hook is inserted immediately before the unique existing
  `r9_5_2_stability_design_basis_decision_dossier_evidence_intake.json` path assignment;
- indentation is derived from those exact live chain lines;
- the entire patched current chain is compiled in memory before any repository file is changed.

## Policy
Package A is recorded as a user-approved PROJECT_ENGINEERING_POLICY for:
- DIAPHRAGM_CONTINUITY
- GLOBAL_BUCKLING_FACTOR
- LOAD_PATH_CONTINUITY
- SECOND_ORDER_AMPLIFICATION
- STOREY_STABILITY_INDEX

Package B project-policy candidates:
- SECOND_ORDER_AMPLIFICATION max 1.10
- GLOBAL_BUCKLING_FACTOR min 11.0
- STOREY_STABILITY_INDEX max 0.10

The 11.0 and 0.10 values remain explicit project-policy proxies, not literal Eurocode numerical clauses.

## Critical safety behavior
The three candidate values are not promoted into actual R9.5 numerical acceptance fields until
licensed/full-source traceability has been completed. R9.5/R9.4/v8.6 remain the qualification gates.
Professional structural review remains required. Production release remains LOCKED.
