# PROJECT PHOENIX — R2D R4 Permanent Opening Rule Engine + Access QA + True 2D/CAD/3D Sync

Status: **PRELIMINARY / NOT FOR CONSTRUCTION**
Design selection: **LOCKED**
Structural solver: **LOCKED**
Permit: **LOCKED**
Construction: **LOCKED**
Professional architect review: **REQUIRED**

## Purpose
R2D R4 converts recurring visual-review corrections into permanent, fail-closed architecture rules. The opening manifest becomes the sole authority for plan, CAD and 3D opening identity and geometry.

## Permanent user rules
1. Windows are permitted only on proven exterior boundaries of the total room union.
2. Exterior windows are rendered cyan (`#00D9FF`).
3. Exterior doors are rendered light brown (`#C69C6D`).
4. Every bathroom must have at least one legal exterior window. If the bathroom has no exterior boundary, the run stops with `ROOM_RELAYOUT_REQUIRED`; Phoenix must not invent an internal window.
5. Every design must contain at least one rear or side exterior door in addition to the front-door route.
6. Every room must be reachable by a swing or sliding door. An `OPEN_PASSAGE` does not satisfy this access gate.
7. Duplicate / overlapping doors are forbidden.
8. Required visible access links:
   - A: woonkamer ↔ keuken/eetruimte
   - B: woonkamer ↔ keuken/eetruimte
   - C: trap ↔ keuken/eetruimte
   - D: trap ↔ keuken/eetruimte
   - E: woonkamer ↔ keuken/eetruimte
9. Non-authoritative long cyan/glass façade-strip geometry is forbidden in Variant A.
10. The exact same opening IDs must exist in 2D SVG, FreeCAD audit and Blender audit, with geometry within configured tolerances.

## Geometry authority
### Exterior windows
A window passes only when five samples across its full width pass a global-room-union XOR test: one side occupied, one side empty, with a consistent outside side. A window on a shared/internal wall is removed before CAD/3D generation.

### Bathroom window auto-repair
If a bathroom has an exposed exterior segment, Phoenix places a collision-free window on that segment and records the repair in `R2D_R4_RULE_ENGINE_REPORT.json`. If no exterior segment exists, the run fails closed before heavy CAD/render work.

### Door access auto-repair
Phoenix builds a room adjacency graph using only real doors. Missing required connections are added only on exact shared room boundaries. Remaining disconnected rooms are connected iteratively through collision-free shared boundaries. No floating door is created.

### Rear / side door auto-repair
If no rear or side door exists, Phoenix selects a collision-free exterior segment on a preferred service room and adds a legal rear or side door. Front/south alone is insufficient.

## Permanent architecture integration
The current `r10_2_optimizer.py` is updated so every A-E design carries the tag `r2d_r4_permanent_opening_rule_engine_required` and declares the opening-rule gate as required before CAD or render generation. This makes R2D R4 part of the architectural design contract rather than a one-off repair script.

## Pipeline order
1. Load current opening manifest.
2. Remove duplicate doors.
3. Remove internal/non-boundary windows.
4. Convert required open passages to real doors or add a legal shared-boundary door.
5. Repair room reachability.
6. Add missing bathroom exterior windows.
7. Add missing rear/side exterior door.
8. Apply fixed 2D/3D style tokens.
9. Regenerate all floorplans from the repaired manifest.
10. Rebuild FreeCAD openings from the same IDs.
11. Rebuild Blender openings from the same IDs.
12. Remove forbidden long cyan Variant-A geometry before authoritative window rebuild.
13. Validate exact ID and geometry sync.
14. Create evidence and visual-review package.

## Release rule
A machine PASS is never a professional visual PASS. Final status remains `PASS ... VISUAL_REVIEW_REQUIRED` until the user approves A–E visually. Construction/permit/solver locks remain unchanged.
