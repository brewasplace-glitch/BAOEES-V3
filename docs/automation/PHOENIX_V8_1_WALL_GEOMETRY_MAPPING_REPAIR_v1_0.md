# Phoenix v8.1 wall geometry mapping repair v1.0

## Scope

This repair changes only the v8.0-to-v8.1 wall geometry mapping in `phoenix/autonomy/structural_session_chain.py`.

- Canonical architectural wall endpoints are read from explicit `start: [x, y]` and `end: [x, y]` fields.
- The legacy `x1_m`, `y1_m`, `x2_m`, `y2_m` contract remains accepted only when all four fields are explicit.
- Missing, non-finite, identical, or length-inconsistent endpoints fail closed. There is no zero-coordinate fallback.
- Wall height is copied from explicit wall `height_m`; no storey-height default is used for wall geometry.
- The mapping register records source-backed endpoints and height, mapped count, source schemas, and `design_values_invented: false`.

## Safety boundary

This repair does not assign materials, sections, loads, combinations, supports, solver properties, or design values. It adds no structural engine and no solver. CalculiX remains the primary existing solver path and OpenSees remains the existing fallback path.

The real mosque workflow must remain blocked at the explicit material/section solver-basis gate until qualified project inputs exist. Formal release remains `LOCKED`; all output remains not for construction and requires professional structural review.

## Verification

The focused regression covers canonical endpoints, explicit legacy endpoints, canonical precedence, and fail-closed invalid geometry. The real Level A run additionally verifies eight non-degenerate wall shells against their architectural source coordinates while confirming that solver input is still blocked for missing material and section data.
