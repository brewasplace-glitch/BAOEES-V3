# PHOENIX 4.41 — Anijstraat #616 Solver Execution + Element Verification

## Purpose

This stage consumes the already-passed Structural Derivation + Load Model and executes a real OpenSeesPy linear-elastic verification model.

Primary gate:
- OpenSeesPy 3.8.0.0 actual execution;
- reaction equilibrium cross-check;
- deflection cross-check against a closed-form beam solution.

Independent fallback:
- a CalculiX beam deck is always generated;
- if Phoenix finds a local `ccx*.exe`, it is executed and evidence is retained;
- fallback availability does not replace the mandatory OpenSees primary gate.

## Element families checked

- source 2x3 timber purlin at 900 mm spacing;
- source 2x4 timber rafter;
- RC ring beam 100x200 source proposal;
- RC column 200x200 with 4D12 source proposal;
- 800x200 strip footing;
- 1000x1000x200 pad footing;
- 2.0 m³ elevated tank gravity foundation envelope.

## Deliberate limitations

The actual unsupported timber spans are still drawing-semantic/topology-sensitive. Therefore Phoenix checks 1.55 m, 2.00 m and 3.40 m explicitly instead of pretending one span is proven.

Wind remains a sensitivity study only. Geotechnical settlement, a legally confirmed Suriname code basis, exact timber grade, tank support geometry and full professional structural review remain release blockers.

Source PDF SHA256: `1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0`

`PRELIMINARY_NOT_FOR_CONSTRUCTION = TRUE`
`FOR_CONSTRUCTION_RELEASE = LOCKED`


## Windows runtime recovery

The first real Windows execution exposed an OpenSeesPy native DLL import blocker.
This is treated as an upstream/runtime issue, not as structural-analysis evidence.

FIX R1 therefore uses a deterministic runtime chain:

1. OpenSeesPy 3.8.0.0 remains the preferred solver and is attempted.
2. PyNiteFEA 3.0.0 is installed in an isolated Phoenix runtime and must actually execute.
3. PyNite reactions and midspan deflections must pass equilibrium/closed-form checks.
4. CalculiX remains the independent fallback/cross-check when a local `ccx` executable exists.

A Phoenix PASS requires a real open-source solver execution. Analytical formulas alone cannot satisfy the gate.
