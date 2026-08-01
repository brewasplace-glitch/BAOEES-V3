# PROJECT PHOENIX — Structural Action and Load Model Generation Engine v8.2.0

## Purpose

v8.2.0 converts explicit project action inputs and the solver-neutral analytical model from v8.1.0 into a traceable structural action/load model candidate.

## Generated entities

- solver-neutral load cases;
- permanent, variable, wind and other explicitly configured action categories;
- solver self-weight flags without inventing numeric member weights;
- nodal, line, area and acceleration action assignments;
- target resolution by element ID or analytical element type;
- explicit ULS/SLS or other project-defined load combinations;
- unit-system and action-basis contract;
- action-to-assignment traceability;
- Central Digital Twin action/load writeback contract.

## Safety boundary

The engine does not invent normative values, occupancy loads, wind pressures, snow actions, seismic actions or combination coefficients. Those values must be supplied by validated project input or a later standards engine.

Unknown analytical targets generate warnings and never create fake assignments. All objects remain `CANDIDATE_ONLY`.

Automatic structural approval is disabled. Solver execution and structural model release remain locked until the action basis, preliminary sizing, solver adapter, solver results, code checks and engineering review have passed.

## Downstream sequence

The intended next Phoenix structural blocks are:

1. preliminary member and shell sizing;
2. solver-adapter generation;
3. structural analysis and result normalization;
4. code-check validation;
5. engineering review and release-gate validation.

## Idempotent installation

The installer accepts both a new verified installation and a fully verified already-installed implementation as success. It commits and pushes only when the expected v8.2.0 targets actually changed.
