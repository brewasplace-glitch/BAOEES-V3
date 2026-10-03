# Project Phoenix 4.41 — Phase 17 Multidisciplinary Engine Suite v1.0

Phase 17 binds fourteen engineering disciplines into one deterministic Digital Twin workflow: electrical, fire safety, water supply, sewer design, BIM, GIS, geotechnical, structural steel, concrete, hydraulics, road design, traffic, sustainability, and climate control/HVAC.

## Governance boundary

- Every discipline is registered with exactly one read-only governed adapter.
- Dependencies must complete in the declared order.
- Missing verified project inputs produce `HOLD_MISSING_VERIFIED_INPUTS`.
- Missing external software is reported and is never simulated.
- No third-party software is installed or activated automatically.
- No repository mutation or professional release is performed by a discipline adapter.
- Final calculations and drawings retain their applicable professional-review boundary.

## Climate-control stack

The primary calculation route is EnergyPlus with OpenStudio as the model/workflow layer. NIST CONTAM is registered for multizone airflow and indoor-air-quality analysis. OpenModelica with the Modelica Buildings Library is registered as an advanced dynamic-controls route. These backends remain unavailable until separately installed, version-qualified, hash-verified, and governed.

## Existing capability reuse

Phase 17 reuses the existing QGIS, BIM coordination, IFC synchronization, GIS/geotechnical bootstrap, EnergyPlus, OpenSees, CalculiX, steel, and concrete adapters. The new suite does not claim these partial capabilities are equivalent to final discipline design. Instead it exposes their evidence, required inputs, declared outputs, unavailable backends, and release holds through one stable result contract.

## Workflow result

The suite produces exactly fourteen ordered engine rows and a deterministic SHA-256 digest. Each row includes dependencies, missing verified inputs, backend availability, intended outputs, existing bindings, and the professional-release boundary.
