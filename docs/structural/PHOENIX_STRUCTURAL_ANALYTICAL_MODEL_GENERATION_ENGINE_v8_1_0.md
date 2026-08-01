# PROJECT PHOENIX — Structural Analytical Model Generation Engine v8.1.0

## Purpose

v8.1.0 converts the structural candidates produced by the Architectural-to-Structural Model Derivation Engine v8.0.0 into a solver-neutral analytical structural model candidate.

## Generated analytical entities

- deduplicated analytical nodes;
- column, beam and roof-support line members;
- loadbearing-wall and slab shell panels;
- provisional boundary-condition/support candidates;
- connectivity graph;
- topological load-path graph;
- material candidates;
- preliminary section candidates;
- transferred stability zones;
- source-to-analytical-element traceability;
- Central Digital Twin writeback contract.

## Safety boundary

This engine does **not** perform final structural design. It does not invent design actions, solver results or code compliance. All generated structural objects remain `CANDIDATE_ONLY`.

Automatic structural approval remains disabled and structural model release remains locked until downstream load modelling, preliminary sizing, solver analysis, code checks and engineering review are completed.

## Downstream sequence

The intended next Phoenix structural blocks are:

1. action and load model generation;
2. preliminary member/shell sizing;
3. solver-adapter generation (OpenSees/CalculiX and future engines);
4. structural analysis/result normalization;
5. code-check and release-gate validation.

## Idempotent installation

The v8.1.0 installer treats an already-present, fully verified implementation as success. No staged files is only an error when the expected payload is not already tracked and valid.
