# PHOENIX R4 FIX R3 — Open-Source Spatial Topology Engine Integration

## Open-source-first decision

R4 FIX R3 replaces Phoenix's hand-written spatial placement engine with an adapter around existing open-source engines.

Primary synthesis:
- Google OR-Tools CP-SAT
- License: Apache License 2.0
- Role: discrete room-to-slot optimization and strategy-specific adjacency objective.

Geometry relations:
- Shapely
- Role: true rectangle geometry distance/intersection checks.

Graph / circulation:
- NetworkX
- Role: connected components, isolates and graph validation.

AEC topology candidate reviewed:
- TopologicPy
- Role reserved for deeper non-manifold topology / graph / semantic BIM integration in the next integration stage.

Downstream engines already retained:
- IfcOpenShell for IFC/BIM authoring.
- FreeCAD BIM for parametric geometry/BIM validation.

Phoenix custom code is limited to:
- adapters;
- strategy objective weights;
- orchestration;
- governance;
- evidence;
- fail-closed validation.

## Commit gate

The installer must pass:
- open-source dependency probe;
- R4 FIX R3 unit tests;
- R3/R2/R1 regressions;
- Phase-19 regressions;
- real-spatial/IFC regressions;
- live Plutostraat pre-commit smoke;
- score spread greater than 2.28;
- 5 SVG + 5 IFC artifacts;
- clean scope/diff gates.

Status: `CONCEPT_GEOMETRY_SYNTHESIS_NOT_FOR_CONSTRUCTION`.
