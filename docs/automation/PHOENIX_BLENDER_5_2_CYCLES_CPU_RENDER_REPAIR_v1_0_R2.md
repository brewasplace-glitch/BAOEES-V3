# PROJECT PHOENIX — Blender 5.2 Cycles CPU Render Repair v1.0 R2

## Bound baseline
`project-phoenix` @ `1a9ddb44256f05e6e355d4e5ee3818c3521aa10e`

## Confirmed failure chain
The R1 smoke proved that:
- Blender 5.2.0 LTS accepts `BLENDER_EEVEE`;
- `scene.world` also needs explicit creation in a clean background scene;
- after those compatibility fixes, Eevee itself fails on the current OpenGL stack because
  `GL_ARB_shader_draw_parameters` is not supported;
- Blender then terminates with `EXCEPTION_ACCESS_VIOLATION`.

This is not an IFC, A–E design, router or project-data failure. It is a headless Eevee/GPU
compatibility failure.

## R2 repair
R2 makes `CYCLES` the primary render engine and explicitly requests CPU rendering:
- `scene.render.engine = CYCLES`
- `scene.cycles.device = CPU`
- `scene.cycles.samples = 16`
- safe world creation when `scene.world is None`

Fallback order remains:
`CYCLES -> BLENDER_EEVEE_NEXT -> BLENDER_EEVEE -> BLENDER_WORKBENCH`

## Evidence gates
Before any commit, the installer must render the already-proven Moskee IFC-derived OBJ with
Blender 5.2 and prove:
- real PNG exists;
- PNG size >= 1000 bytes;
- `PHOENIX_RENDER_ENGINE=CYCLES`;
- `PHOENIX_RENDER_DEVICE=CPU`;
- `PHOENIX_WORLD_READY=PASS`.

After successful build gates, the installer performs BIB sync/validation, commit/push,
clean/sync validation and automatically reruns the full Moskee Bunschoten real-project E2E.

No DE TV core, nonresidential router, Integrated Suite, IFC adapter or Blender adapter contract
is modified. Production and FOR CONSTRUCTION remain locked.
