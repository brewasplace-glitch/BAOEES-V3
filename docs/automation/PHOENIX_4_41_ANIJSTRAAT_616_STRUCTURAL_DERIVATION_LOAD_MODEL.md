# PHOENIX 4.41 — Anijstraat #616 Structural Derivation + Load Model

Consumes the already-approved Structural Input + Gap Analysis plus the exact 15-page design source (`1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0`).

Outputs: drawing grid/levels, preliminary load path, characteristic load model, soil/wind/timber sensitivity registers, explicit authority decisions, and OpenSees + CalculiX global-envelope solver seeds.

The solver seeds are pipeline/global-envelope seeds only; detailed wall/roof support vectors are not yet mapped and solver execution is intentionally disabled in this stage.

`PRELIMINARY_NOT_FOR_CONSTRUCTION = TRUE`
`FOR_CONSTRUCTION_RELEASE = LOCKED`

Next: `PHOENIX 4.41 REAL-PROJECT SOLVER EXECUTION + ELEMENT VERIFICATION — ANIJSTRAAT #616`
