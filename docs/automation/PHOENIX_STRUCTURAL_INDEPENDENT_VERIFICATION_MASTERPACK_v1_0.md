# PROJECT PHOENIX — Structural Independent Verification Masterpack v1.0

## Baseline

`b1a0605d8cadd349e7b5baca22e71397a18dbcef`

## Purpose

This layer verifies structural calculation evidence before professional review.

It is solver-independent at the orchestration level, with SCIA as primary professional
calculation engine and CalculiX as the secondary numerical verification engine.

## Verification categories

1. source SCIA execution/evidence status;
2. global static equilibrium;
3. analytical/hand-calculation spot checks;
4. load-path completeness;
5. solver/log health;
6. SCIA versus CalculiX result comparisons;
7. mesh-convergence studies;
8. sensitivity studies;
9. evidence file integrity / SHA-256.

## No invented tolerances

Phoenix v1.0 contains **no default numerical acceptance tolerances** for:
- equilibrium;
- solver-to-solver differences;
- mesh convergence;
- analytical spot checks;
- sensitivity no-change criteria.

Every required limit must be supplied in the project verification plan or the check remains
`VERIFICATION_INPUT_REQUIRED`.

## Status model

- `CALCULATED_UNVERIFIED` — source solver only.
- `TECHNICALLY_VERIFIED` — all required technical checks pass, without a required/passing second-solver cross-check.
- `TECHNICALLY_CROSS_VERIFIED` — all required technical checks pass including SCIA↔CalculiX comparisons.
- `PROFESSIONALLY_REVIEWED` — deliberately outside this engine.

## Important boundary

CalculiX is a second numerical solver. A SCIA/CalculiX match does **not** constitute an
independent professional review.

Production and FOR-CONSTRUCTION remain `LOCKED`.
