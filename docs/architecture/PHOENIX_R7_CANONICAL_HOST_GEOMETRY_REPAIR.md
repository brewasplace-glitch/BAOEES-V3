# PHOENIX R7 — Canonical Host Geometry Repair

R7 repairs a systemic post-optimization consistency defect: final optimized room
geometry could diverge from walls/openings that had been derived earlier.

Implementation:
- reuses existing `real_spatial._derive_walls()` and `_derive_openings()`;
- executes at `write_layout_bundle()` after spatial optimization and before JSON/SVG;
- `author_ifc4()` defensively invokes the same idempotent finalizer;
- regenerates walls and openings from final room coordinates;
- creates explicit `windows`, `doors`, `opening_sides`, and N/E/S/W `facades`;
- synchronizes room `area_m2` with final width/depth;
- binds roof metadata to the final footprint;
- fails closed when any opening is not on its host wall or outside the host span.

Open-source-first remains unchanged:
IfcOpenShell is the downstream IFC author/validator, FreeCAD BIM is the secondary
BIM verification layer, TopologicPy remains the topology engine, and Shapely is
the planar-geometry helper. R7 custom code is orchestration, canonicalization and
governance glue only.

Release status remains concept-only / not for construction.
