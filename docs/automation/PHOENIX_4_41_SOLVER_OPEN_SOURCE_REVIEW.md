# PHOENIX 4.41 — Solver Open-Source Review — FIX R1

## Preferred — OpenSees / OpenSeesPy

OpenSeesPy 3.8.0.0 remains the preferred advanced solver interface.
The first Windows real-project run installed it successfully but the native module failed to import with a DLL-load error.
Phoenix records this as `BLOCKED_NATIVE_RUNTIME`; it is not converted into a numerical PASS.

## Operational runtime fallback — PyNiteFEA 3.0.0

PyNiteFEA is an MIT-licensed 3D frame/beam finite-element library.
Phoenix installs it into an isolated user-local runtime and executes the same representative beam cases.
Reaction equilibrium and deflections are independently checked against closed-form solutions.
When OpenSees is blocked, PyNite becomes `PRIMARY_RUNTIME_FALLBACK_AFTER_OPENSEES_NATIVE_BLOCKER`.

## Independent fallback — CalculiX

Phoenix continues to discover a local `ccx*.exe` and executes a generated beam deck when available.
The deck is always retained even if the executable is not installed.

## Governance

A solver execution PASS remains preliminary engineering evidence only.
It does not establish Suriname legal code compliance, geotechnical adequacy, confirmed timber grading or for-construction approval.
