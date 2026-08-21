# PROJECT PHOENIX — Generic / Institutional / Nonresidential Reuse Router v1.0

## Purpose
The Moskee Bunschoten real-project E2E proved that `tropical_residential` is semantically wrong for this project. A separate reuse-first nonresidential route is required.

## Reuse-first architecture
This build does **not** create a second complete architectural stack. It reuses existing tracked Phoenix components:

- `phoenix.architecture.integrated_suite_v4_0_0` for generic spaces, drawings and concept review findings;
- `phoenix.architecture.ifc_authoritative_model_adapter_v1_0` for authoritative IFC;
- `phoenix.engines.architectural_visual_pipeline_v1_0` for Blender rendering of that IFC;
- installed FreeCAD for independent IFC → FCStd handoff.

Only a thin nonresidential A–E transformation/orchestration layer and a compatibility route are added.

## Source grounding
Moskee Bunschoten variants are derived from tracked project evidence:

- architectural model v4.0.0 — levels, walls, openings, stairs, assembly spaces;
- central geometric model v1.0.0 — existing building, site and 7 × 10 m / 140 m² extension;
- real concept production v1.0.0 — geometry and occupancy basis.

No bedroom/bathroom residential program is fabricated.

## Governance
All outputs remain concept candidates. Automatic professional approval is disabled. Production and FOR CONSTRUCTION remain locked.
