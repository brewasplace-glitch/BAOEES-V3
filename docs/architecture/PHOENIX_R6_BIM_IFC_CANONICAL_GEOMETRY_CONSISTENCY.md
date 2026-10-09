# PHOENIX R6 — BIM / IFC Canonical Geometry Consistency

Open-source-first stack:
- IfcOpenShell: primary IFC parser, schema validator and geometry engine.
- FreeCAD BIM / Native IFC: secondary headless geometry verification when available.
- Shapely remains the planar geometry utility already used elsewhere in Phoenix.

R6 validates that persisted Phoenix room geometry and generated IFC/SVG evidence
represent the same canonical design rather than stale pre-R4/R5 geometry.

Hard checks:
- IFC opens successfully;
- IfcOpenShell schema validation has no ERROR/CRITICAL findings;
- geometry iterator produces geometry;
- IfcSpace geometry covers all canonical rooms;
- room-to-space relative centre/width/depth differences <= 0.35 m;
- IFC contains walls;
- opening elements and IfcRelVoidsElement coverage are coherent;
- SVG contains geometry primitives.

The comparison is translation-invariant so a legitimate common site-origin offset
does not falsely fail room placement. Relative topology and dimensions must still match.

If current IFC authoring does not yet write IfcSpace or writes stale room/wall/opening
geometry, the real-project precommit smoke fails and R6 is not committed.

Release boundary: CANONICAL_GEOMETRY_QA_NOT_FOR_CONSTRUCTION.
