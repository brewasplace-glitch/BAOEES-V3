# Project Phoenix R9.1 — Advanced Stability Evidence Completion & Qualification Masterpack v1.0

## Purpose

R9.1 runs after R9 when R9 has produced technical evidence but cannot yet build the full v8.6 nine-check input contract. R9.1 makes the difference between "evidence exists" and "the check is qualified for v8.6" explicit.

## Added technical evidence

- Reuses real CalculiX NLGEOM second-order evidence from R9.
- Runs real CalculiX linear eigenvalue-buckling cases for lateral base cases in live mode and records the lowest positive load factor when the solver produces a parseable result.
- Derives storey P, V, drift, candidate stability index and secant stiffness from the v8.3 equivalent-nodal-load ledger plus R9/v8.4 response evidence.
- Reports adjacent-storey stiffness-ratio candidates without selecting a normative reference method.
- Reuses R9 torsional nodal-drift-spread, diaphragm-connectivity and load-path-connectivity evidence.
- Adds single-member-removal graph-connectivity evidence, explicitly labelled topology-only and not alternate-load-path capacity.

## Qualification states

Each required v8.6 check is classified as evidence/reference/limit/analysis required instead of reporting all technical evidence as absent. R9.1 only creates a complete v8.6 input when all nine checks are supported by explicit traceable source references and all required limits or engineering evidence are present.

## CalculiX basis

The CalculiX CrunchiX manual documents `*BUCKLE` as the linear buckling procedure, states that the lowest eigenvalue is the load multiplier (buckling factor), and that buckling factors are written to the `.dat` file. R9.1 requests one factor and records the raw deck/output as evidence. It does not infer the minimum acceptable factor.

Reference used for implementation: CalculiX CrunchiX User's Manual, keyword `*BUCKLE`, https://www.dhondt.de/ccx_2.21.pdf .

## Safety

- No normative limit invention.
- Generic v8.6 example thresholds remain forbidden as project evidence.
- Weak-storey strength remains explicit engineering analysis unless traceable input exists.
- Alternate-load-path topology evidence is not promoted to capacity evidence.
- No automatic code-compliance claim.
- No automatic structural or robustness approval.
- Professional structural review remains required.
- For-construction / production release remains LOCKED.
