# PROJECT PHOENIX — Architectural Delivery Manifest Collector Contract Repair v1.0

## Bound baseline
`project-phoenix` @ `68851cd424c3037a2b7d54dc738484f305908341`

## Proven blocker
The Moskee nonresidential orchestration exits with process return code `0` and emits a valid
result object containing `recommended_variant_id = E` and the real
`manifest_path = .../delivery/nonresidential_reuse_v1/delivery_manifest.json`.

The manifest exists, but `phoenix/local_app/architectural_orchestration_runtime.py`
hard-codes `delivery/architectural_ae_v1_0/delivery_manifest.json` in both `plan()` and
`_run()`.

## Repair
- route-aware planned manifest path;
- consume `manifest_path` from the successful CLI result contract in `workflow.log`;
- validate project identity;
- constrain the manifest to the project's runtime directory;
- preserve the legacy residential manifest fallback.

A–E generation, Integrated Suite, IFC, Blender/Cycles, FreeCAD and DE TV content are
unchanged. Production and FOR CONSTRUCTION remain locked.
