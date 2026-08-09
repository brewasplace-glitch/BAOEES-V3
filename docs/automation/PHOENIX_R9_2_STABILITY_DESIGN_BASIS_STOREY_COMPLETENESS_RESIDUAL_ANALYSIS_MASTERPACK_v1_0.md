# PROJECT PHOENIX R9.2 — Stability Design Basis, Storey Completeness & Residual Analysis

Version: 1.0

## Purpose
R9.2 executes after R9.1 when v8.6 is still blocked. It does not loosen v8.6. It verifies that the analytical structural model contains every architecturally expected storey boundary, including the top of the top storey when an explicit height is available.

## Added evidence controls
- Structural storey-model completeness gate with expected-versus-detected elevations and vertical load-path interval evidence.
- Reconstructed first-order floor response on expected structural levels.
- Torsional-drift candidate filtering that excludes base/support and near-zero numerical-noise rows.
- Reconstructed storey P/V/drift/secant-stiffness mechanics and adjacent-storey ratio candidates when multiple complete storey intervals exist.
- Explicit traceable contracts for weak-storey strength and alternate-load-path capacity; neither is invented from topology alone.
- Project stability-design-basis input template with null normative limits until traceable project/standards evidence is supplied.

## Fail-closed behavior
If an architectural storey boundary or vertical structural interval is missing, R9.2 returns `R9_2_STRUCTURAL_STOREY_MODEL_INCOMPLETE` before v8.6. If the storey model is complete but limits/references or residual capacity analyses are missing, it returns `R9_2_STABILITY_DESIGN_BASIS_OR_RESIDUAL_EVIDENCE_REQUIRED`.

## Safety
Automatic code-compliance, structural approval and robustness approval remain disabled. Professional structural review is required. Production/for-construction release remains LOCKED. Generic v8.6 example thresholds are forbidden as project evidence.
