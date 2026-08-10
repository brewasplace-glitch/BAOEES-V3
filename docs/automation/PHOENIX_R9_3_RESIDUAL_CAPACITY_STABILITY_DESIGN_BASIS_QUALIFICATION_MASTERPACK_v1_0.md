# PROJECT PHOENIX R9.3 – Residual Capacity & Stability Design-Basis Qualification

## Purpose

R9.3 executes after R9.2 has proved the storey model complete but v8.6 is still
blocked. It closes the remaining technical-evidence gap without weakening the
existing v8.6 verifier.

## Technical evidence

R9.3 derives two new evidence classes:

1. `R8_RC_SCREENING_RESISTANCE_DERIVED_STOREY_CAPACITY_PROXY`
2. `TOPOLOGY_PLUS_TRACEABLE_CAPACITY_RESERVE_SCREENING`

The first aggregates only traceable R8 RC candidate screening resistances for
vertical members in each R9.2 storey interval. The second combines R9.1
single-member-removal topology evidence with the traceable residual capacity
proxy after removal.

Neither evidence class is a normative resistance or nonlinear redistributed
alternate-path analysis.

## Qualification contract

R9.3 creates one project input template:
`r9_3_stability_design_basis_input`.

A check is promoted into the existing v8.6 candidate check set only when the
project input explicitly supplies the required engineering-scope acceptance,
limit/reference, or an explicit check record.

Generic v8.6 example values are forbidden.

## Safety

- No normative limits are invented.
- R8 RC screening resistances are not silently promoted to verified code resistances.
- Member-removal demand redistribution is not fabricated.
- Automatic code-compliance, structural approval and robustness approval remain disabled.
- Professional structural review remains required.
- Production / for-construction release remains locked.
