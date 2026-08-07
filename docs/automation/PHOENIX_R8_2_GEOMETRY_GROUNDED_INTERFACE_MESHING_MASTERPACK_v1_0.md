# Project Phoenix R8.2 — Geometry-Grounded Structural Interface Meshing

R8.2 follows the R8.1 fail-closed topology gate. It repairs only interfaces whose geometry is already explicitly present in the analytical model.

## Allowed automatic repairs

- split an existing line member where an existing member endpoint lies on that member segment;
- insert an existing endpoint node on an existing shell edge;
- insert an existing endpoint node inside one unique allowed existing slab face;
- triangulate only the affected shell parent while conserving its geometric area;
- remap distributed `self_weight`, `line`, and `area` actions to the split child elements while preserving the per-unit magnitude.

## Explicitly prohibited

R8.2 does not invent supports, columns, beams, material values, rigid links, ties, multi-point constraints, springs, code parameters, professional approval, or construction release. Unknown element-targeted action types fail closed.

## Solver compatibility

Affected shell parents become 3-node shell children. v8.3 is extended deterministically:

- OpenSees: 3 nodes -> `ShellDKGT`; 4 nodes -> `ShellMITC4`;
- CalculiX: 3 nodes -> `S3`; 4 nodes -> `S4`.

After R8.2, R8.1 is executed again as a post-meshing gate. The chain continues to v8.3 only when that post-validation passes.

## PAT evidence motivating this capability

The R8.1 PAT identified 11 unresolved endpoints. Six already had member-segment or shell-edge evidence. A follow-up geometry classification proved the remaining five points lie inside existing slab faces. R8.2 generalizes that evidence-driven repair rather than hard-coding project IDs.

Production / for-construction release remains `LOCKED` and professional structural review remains required.
