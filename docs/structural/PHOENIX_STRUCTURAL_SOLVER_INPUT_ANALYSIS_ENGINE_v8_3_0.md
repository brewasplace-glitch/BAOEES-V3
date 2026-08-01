# PROJECT PHOENIX — Structural Solver Input and Analysis Engine v8.3.0

## Purpose

v8.3.0 converts the solver-neutral structural analytical model and explicit action/load model into traceable solver packages for OpenSees and CalculiX. It also defines the execution and result-normalization contract used by downstream structural verification blocks.

## What v8.3.0 generates

- validated node, member, shell and support maps;
- derived elastic section properties from explicitly supplied section geometry;
- equivalent nodal actions for explicit nodal, line and area loads;
- self-weight from explicit density, geometry and gravity input;
- one linear-static base-case deck per load case for OpenSees;
- one linear-static base-case deck per load case for CalculiX;
- solver-tag and Phoenix-ID mapping manifests;
- load-combination post-processing contract;
- solver execution readiness diagnostics;
- result-normalization schema for displacements, reactions and element forces;
- Central Digital Twin analysis writeback contract.

## Important engineering boundary

The generic project values shipped with this build are demonstration fixtures only and are explicitly labelled `EXPLICIT_DEMONSTRATION_INPUT_NOT_FOR_DESIGN`. The engine never treats these values as normative or project-approved values.

Material properties, densities, section geometry, supports, actions, gravity and combination factors must come from explicit validated project input. v8.3.0 may derive mathematical properties such as area, moments of inertia, torsion approximation, member length, shell area and equivalent nodal loads from that explicit input.

## Solver strategy

Both adapters use solver-native nodes and elements, while loads are converted to traceable equivalent nodal vectors. This keeps global action directions deterministic across adapters and preserves a common Phoenix load mapping.

OpenSees output uses 3D/6-DOF elastic beam-column members and MITC4 shell elements. CalculiX output uses B31 beam members and S4 shell elements. Each base load case is generated as its own solver deck so linear load combinations can be formed from base-case results without silently summing incompatible cases.

## Execution gate

Solver execution is disabled by default. Execution is permitted only when both conditions are true:

1. project `execution_policy.allow_execution` is explicitly true;
2. the CLI is invoked with `--allow-execution`.

An installed solver executable must also be discoverable. A successful solver run does **not** prove code compliance and never grants structural approval.

## Release state

- automatic structural approval: **DISABLED**;
- automatic code-compliance claim: **DISABLED**;
- structural model release: **LOCKED**;
- engineering review: **REQUIRED**.

## Downstream sequence

The next structural blocks should consume normalized base-case solver results to perform result sanity checks, load-combination result synthesis, member/shell verification, stability checks, code checks and ultimately the engineering release gate.

## Idempotent installation

The installer treats a fully verified already-installed v8.3.0 payload as success. It only creates a commit and pushes when one or more expected v8.3.0 targets actually change.
