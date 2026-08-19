# PROJECT PHOENIX AUTONOMOUS ARCHITECTURAL PROJECT ORCHESTRATION + REAL PROJECT A-E DELIVERY v1.0

## Baseline
Required baseline: `2db9e7a748c8ed436e76932b0e39a8977ef9dd75` on branch `project-phoenix`.

## Purpose
This build connects the already proven A-E tropical-residential stack into one project-scoped delivery flow.

The orchestration authority calls the proven real 3D / DE TV pipeline **once**. That pipeline already performs:
A-E design -> real spatial layout -> authoritative IFC -> FreeCAD -> Blender Cycles CPU -> DE TV.

Calling it once avoids duplicate IFC/FreeCAD/Blender work and keeps one authoritative project runtime tree.

## Permanent project runtime
Normal project execution writes to:

`projects/runtime/<PROJECT_ID>/`

The new delivery layer writes:

`projects/runtime/<PROJECT_ID>/delivery/architectural_ae_v1_0/`

with:
- `delivery_manifest.json`
- `orchestration_evidence.json`
- `delivery_summary.md`

The manifest indexes:
- A-E variant summaries
- recommended variant
- authoritative IFC
- authoritative Blend
- FreeCAD FCStd output
- 20 Blender variant renders
- four canonical DE TV APNG presentations

## Existing proven open-source stack
No new engine is introduced in this repair/build:
- Shapely — spatial validation
- IfcOpenShell — authoritative IFC
- FreeCAD — BIM/CAD refinement
- Blender Cycles CPU — real 3D rendering
- Phoenix DE TV sidecar — presentation
- three.js remains a reviewed browser fallback and is not added

## Governance
The delivery remains `CONCEPT_ONLY_NOT_FOR_CONSTRUCTION`.
Production and for-construction release remain locked.
Professional approval is not automatic.
