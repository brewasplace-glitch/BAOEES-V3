# PROJECT PHOENIX TROPICAL RESIDENTIAL REAL SPATIAL LAYOUT + AUTHORITATIVE IFC AUTHORING v1.0

## Purpose
Upgrade the Tropical Residential Design Engine Foundation from schematic variant metadata to real,
non-overlapping room rectangles, derived walls/openings, IFC4 authoring and downstream FreeCAD/Blender handoffs.

## OSS-first architecture
1. **Shapely** — primary planar geometry validation (BSD-3-Clause).
2. **IfcOpenShell** — primary Authoritative IFC4 authoring engine (LGPL-3.0-or-later).
3. **FreeCAD** — BIM/CAD refinement fallback/handoff (LGPL-2.1-or-later).
4. **Blender** — 3D visualization handoff through background Python automation (GPL).
5. **NetworkX** — optional room-graph engine when present (BSD-3-Clause); deterministic adjacency logic remains available.

No package is installed silently.


## Foundation v1.0 compatibility contract
The real-spatial layer is matched to the installed Foundation v1.0 API:
- `generate_variants(project)` returns A-E Variant objects;
- `select_balanced(variants)` selects the current recommended concept;
- Variant stores bedrooms, bathrooms and concept-envelope parameters;
- this layer derives the explicit room programme and does not assume a `rooms` field.

## Real spatial outputs
Each variant A-E contains:
- room rectangles by storey;
- room target and geometric areas;
- external and internal wall segments;
- entrance, window and internal-door opening strategy;
- shaded veranda concept;
- roof pitch/eave metadata;
- Shapely overlap/containment evidence;
- concept site-envelope evidence;
- storey plan SVGs.

## IFC authoring
IfcOpenShell creates a real IFC4 file containing:
- IfcProject / IfcSite / IfcBuilding / IfcBuildingStorey;
- IfcSlab floor geometry;
- IfcWall geometry;
- IfcSpace 3D room volumes;
- IfcOpeningElement relationships;
- IfcDoor / IfcWindow fillings;
- IfcRoof simplified volume with tropical pitch retained in model naming/metadata.

Five candidate IFCs are generated. The currently recommended A-E variant is copied to the
`authoritative/` directory as the current recommended authoritative design model.

## FreeCAD and Blender
The runtime discovery layer checks:
- explicit PHOENIX_FREECAD_EXE / PHOENIX_BLENDER_EXE;
- PATH;
- standard Windows Program Files / LocalAppData installation patterns.

When detected:
- FreeCADCmd builds and saves a real `.FCStd` geometry handoff from the recommended layout.
- Blender runs in background and builds/saves a real `.blend` geometry handoff.

These are downstream derivatives; IFC remains authoritative.

## Governance
This remains design-development output:
- PROFESSIONAL APPROVAL = NOT AUTOMATIC
- CODE COMPLIANCE = NOT AUTOMATIC
- PRODUCTION = LOCKED
- FOR-CONSTRUCTION = LOCKED
