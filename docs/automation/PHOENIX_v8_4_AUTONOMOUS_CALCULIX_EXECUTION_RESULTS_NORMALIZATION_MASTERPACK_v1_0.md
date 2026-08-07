# Project Phoenix v8.4 Autonomous CalculiX Execution + Raw Evidence + Results Normalization Masterpack v1.0

This release connects the existing v8.3 CalculiX base-case decks to the existing v8.4
analysis-results validation contract.

Safety:
- live solver execution only in real autonomous project sessions;
- PHOENIX_TEST_MODE=1 disables live solver execution;
- original v8.3 decks remain unchanged;
- raw .dat/.frd evidence and SHA-256 manifests are required;
- no solver result is fabricated;
- CalculiX RF is normalized as total nodal force minus explicit v8.3 CLOAD;
- member generalized forces come from CalculiX SECTION FORCES;
- stresses come from CalculiX integration-point *EL PRINT output;
- shell force resultants are deferred rather than invented;
- cross-solver comparison is disabled when only CalculiX is available;
- automatic code compliance and professional approval remain disabled;
- production release remains LOCKED.

Executable discovery:
1. PHOENIX_CALCULIX_EXECUTABLE
2. PATH
3. Windows FreeCAD/CalculiX Program Files installations

## FIXED R2 — native CalculiX FRD section-force parsing

The first Windows real-smoke proved that CalculiX itself executed successfully but the FRD section-force parser rejected the native fixed-width ASCII record layout. R2 parses FRD `-1` node/value records without relying on whitespace and normalizes the CalculiX `SZX` component label to Phoenix `SXZ`. Solver execution and raw-evidence requirements are unchanged.

## FIXED R3 — v8.3 solver-package directory contract

The v8.3 writer persists solver files below a solver-specific directory. CalculiX base-case decks therefore live at `v8_3/solver_package/calculix/calculix_<case_id>.inp`. R3 aligns the autonomous v8.4 executor with that exact durable layout. No recursive or fuzzy filename search is used and no solver input is synthesized.
