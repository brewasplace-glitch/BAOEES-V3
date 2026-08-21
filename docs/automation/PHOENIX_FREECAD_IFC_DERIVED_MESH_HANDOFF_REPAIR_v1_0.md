# PROJECT PHOENIX — FreeCAD IFC-Derived Mesh Handoff Repair v1.0

## Bound baseline
`project-phoenix` @ `9b23fd9ecc05d6ea20495fbc69dd708c271456ce`

## Proven blocker
FreeCAD 1.1.1 command-line runtime reports `OSError: no supported file format` for
`Import.insert(authoritative.ifc, doc.Name)`. FreeCAD may still exit with code 0, while no
FCStd is written. The existing output-file gate therefore correctly blocks the handoff.

## Repair
The authoritative model remains IFC. FreeCAD becomes an explicitly derived presentation
handoff:

1. Reuse `phoenix.engines.ifc_visual_mesh_adapter_v1_0.ifc_to_obj`.
2. Load the derived OBJ with FreeCAD's `Mesh` module.
3. Create `Mesh::Feature`.
4. Save a real FCStd.
5. Require a real FCStd >= 1000 bytes and explicit PASS evidence.

No DE TV core, Blender repair, A–E semantics, Integrated Suite or authoritative IFC adapter
is modified. Production and FOR CONSTRUCTION remain locked.
