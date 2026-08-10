# PROJECT PHOENIX R9.5.1 — Project Stability Design-Basis Input & Evidence Qualification Masterpack v1.1

Baseline: `3e2a6cbe2eab81948a55c706d156b670b8baca9d`

R9.5.1 converts the R9.5 required-input template into one project-specific scaffold and consolidates the remaining nine check decisions into five evidence/review packages. It pre-seeds only already-registered Suriname primary-source records (Bouwbesluit Articles 26 and 27) and never invents numerical acceptance limits, seismic applicability, project-policy approval, professional review or alternate-path redistribution proof.

Runtime output:
- `v8_6/r9_5_1_project_stability_design_basis_input_evidence_qualification.json`
- updated `workspace/inputs/structural/global_stability_engineering_input_REQUIRED.json`

Existing R9.5, R9.4 and v8.6 gates remain preserved.

## v1.1 installer fix
The v1.0 runtime patch expected one exact multiline rendering of the R9.5 blocked branch. v1.1 replaces that brittle anchor with structural line-based discovery scoped to the existing R9.5 runtime marker. No R9.5/R9.4/v8.6 safety gate is weakened.
