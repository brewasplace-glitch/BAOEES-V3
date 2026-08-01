# PROJECT PHOENIX — Global Stability, Second-Order & Structural Robustness Verification Engine v8.6.0

## Purpose
v8.6.0 consumes the member-verification candidate from v8.5.0 and creates auditable evidence for whole-structure stability and robustness. It evaluates explicit project rules for second-order sensitivity, storey stability, global buckling indicators, torsional sensitivity, soft/weak storeys, diaphragm continuity, gravity/lateral load-path continuity and alternate-load-path evidence.

## Engineering boundary
The engine deliberately does **not** invent code thresholds, stability-index limits, critical-load-factor limits, drift irregularity limits, soft/weak-storey ratios or robustness criteria. Every threshold must be supplied by the project structural design basis, a verified standards engine, licensed normative dataset or competent engineer input and must carry a source reference.

A `PASS` means only that the configured check evaluates within the explicitly supplied threshold/evidence. It is not a statutory code-compliance declaration and does not constitute signed structural approval.

## Supported checks
- `SECOND_ORDER_AMPLIFICATION` — compares explicit first- and second-order displacement evidence.
- `STOREY_STABILITY_INDEX` — evaluates the explicit P·Δ/(V·h) storey index against an explicit limit.
- `GLOBAL_BUCKLING_FACTOR` — checks an externally generated critical load factor against an explicit minimum.
- `TORSIONAL_DRIFT_RATIO` — checks maximum/average edge-drift ratio against an explicit limit.
- `SOFT_STOREY_STIFFNESS_RATIO` — compares explicit storey/reference stiffness values.
- `WEAK_STOREY_STRENGTH_RATIO` — compares explicit storey/reference lateral strengths.
- `DIAPHRAGM_CONTINUITY` — requires explicit continuity evidence.
- `LOAD_PATH_CONTINUITY` — verifies graph connectivity from loaded nodes to supports.
- `ALTERNATE_LOAD_PATH_EVIDENCE` — requires explicit robustness evidence.

## Hard gates
- v8.5.0 source engine and an accepted member-verification state are mandatory;
- jurisdiction, standard set, edition and stability source reference are mandatory;
- normative references are mandatory for configured checks by default;
- every mandatory global-stability check type must be represented;
- failed or incomplete mandatory checks create review items;
- automatic code-compliance claim remains disabled;
- automatic structural/robustness approval remains disabled;
- structural model release remains locked.

## Digital Twin
Candidate evidence is written conceptually to:

`CENTRAL_DIGITAL_TWIN.structural.global_stability_second_order_robustness`

The writeback preserves check results and normative references for later audit and competent-engineer review.

## Remaining release-gate capabilities
v8.6.0 intentionally leaves these gates closed for subsequent Phoenix build blocks:
1. connection and support verification;
2. foundation-interface verification;
3. competent engineering review / release gate.
