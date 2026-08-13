# PROJECT PHOENIX — Structural Model Interchange + SCIA Project Preparation + Environment Readiness v1.0

## Required baseline

`f676a2bd070e5cbf4dea3f2adbe9b8b7f73a7f10`

## Purpose

This masterpack closes the solver-interface gap without requiring a working SCIA licence during installation.

### Layer A — Canonical Structural Model

Phoenix gets one solver-neutral structural representation containing:

- nodes;
- members;
- materials;
- sections;
- supports;
- load cases;
- nodal and line loads;
- load combinations;
- units;
- metadata.

The engine validates ID uniqueness and cross-references before any solver-specific preparation is allowed. A deterministic canonical SHA-256 is produced for traceability.

### Layer B — SCIA Project Preparation

Phoenix can prepare and hash:

- an existing `.ESA` seed;
- an XML update file;
- an XML definition file;
- the canonical model;
- a SCIA object-mapping plan;
- a project-specific calculation plan;
- a command plan;
- an evidence manifest.

Phoenix v1.0 deliberately does **not** synthesize the proprietary binary `.ESA` format and does not fabricate SCIA object IDs.

Preparation states include:

- `SCIA_MODEL_BUILD_REQUIRED`
- `SCIA_SEED_PRESENT_XML_MAPPING_REQUIRED`
- `SCIA_ANALYSIS_SCOPE_REQUIRED`
- `SCIA_SEED_XML_PREPARATION_READY`

A preparation-ready package is still not a calculated or verified model.

### Layer C — SCIA Environment Readiness

The readiness layer is read-only by default. It may inspect:

- `ESA_XML.exe`;
- `ESA.exe`;
- `Lockman.exe`;
- Windows service state;
- an explicitly supplied `PORT@HOST` floating-licence target;
- the built-in ESA_XML help signature.

It never starts, stops or reconfigures a service and never modifies licence configuration.

The SCIA Engineer 18.1 built-in ESA_XML help observed on the target machine defines:

- 0 — Succeeded
- 1 — Unable to initialize MFC
- 2 — Missing arguments
- 3 — Invalid arguments
- 4 — Unable to open ProjectFile
- 5 — Calculation failed
- 6 — Unable to initialize application environment
- 7 — Error during update ProjectFile by XMLUpdateFile
- 8 — Error during create export outputs
- 9 — Error during create XML outputs
- 10 — Error during update ProjectFile by XLSX Update

The current licence problem can therefore later be classified explicitly as:
`BLOCKED_SCIA_APPLICATION_ENVIRONMENT`.

### Explicit live-probe gate

A real SCIA probe is impossible unless the runner is invoked with:

`-AllowLiveProbe`

The installer never invokes that action.

## Safety boundaries

- no automatic professional approval;
- no automatic code-compliance claim;
- no production release;
- no FOR-CONSTRUCTION release;
- no automatic seismic/nonlinear/robustness scope;
- no solver readiness status may be treated as engineering approval.
