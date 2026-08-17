# PROJECT PHOENIX PAT-002 REAL IFC -> BLENDER RENDER + DE TV ACTIVATION v1.0

## Purpose

Activate a real presentation path for PHOENIX-PAT-002 using the authoritative IFC model and the
installed Blender engine.

Required baseline:

`440591ada89420ff557906be0a99d89fcd2c416a`

## Automatic PAT-002 render path

For project `PHOENIX-PAT-002` only:

1. Phoenix generates the selected architectural design variant.
2. IfcOpenShell generates the authoritative IFC.
3. Phoenix derives an OBJ mesh from IFC geometry.
4. Blender runs headless.
5. Blender generates:
   - `phoenix_exterior_front.png`
   - `phoenix_exterior_rear.png`
   - `phoenix_bird_view.png`
   - `phoenix_interior_cutaway.png`
6. Phoenix writes a Blender presentation manifest and updates the architectural state and Digital Twin.
7. DE TV can semantically open those exact project-scoped images.

Other projects remain unchanged in v1.0.

## Interior cutaway

The initial interior presentation is a deterministic cutaway:
- roof objects are hidden for the interior frame;
- the front-most wall group is hidden where discoverable;
- the camera looks into the IFC-derived building volume.

This is intended to prove a real geometry-based interior presentation route. It is not yet a furnished,
photorealistic interior-design scene.

## DE TV commands

For active project `PHOENIX-PAT-002`:

- `toon ontwerp`
- `toon exterieur`
- `toon interieur`
- `toon variant B`
- `toon 3D`
- `toon vogelvlucht`
- `toon achtergevel`

The TV adapter uses the existing authoritative active-project context and exact-artifact render bridge.

It does not search artifacts from other projects.

## Authority and safety

IFC remains authoritative geometry.

Blender PNGs are presentation artifacts only.

No Blender output is promoted to IFC automatically.

Professional review remains required.

Production release remains LOCKED.

## Regression strategy

The pack runs:
- one real temporary PAT-002 architecture execution;
- real IFC generation;
- real IFC-to-OBJ derivation;
- real headless Blender rendering;
- PNG existence/size/header validation;
- manifest and Digital Twin authority checks;
- non-PAT project scope regression;
- DE TV routing contract tests;
- existing architecture, BIM-Lite, IFC, visual-engine and DE TV regressions.

## Commit/push safety

All tests, scope checks and `git diff --check` run before commit.

The working tree must be clean immediately after commit and before push.

Once pushed, the installer never destructively resets the pushed commit.

## R1 render-quality gate

The original v1.0 gate treated every PNG below 10,000 bytes as missing. That is too coarse for simple
Eevee scenes because valid 1280x720 PNGs with large uniform backgrounds may compress below that size.

R1 validates each render by:
- file existence;
- PNG signature;
- IHDR presence;
- width >= 1280;
- height >= 720;
- size >= 1500 bytes;
- Blender scene-evidence marker.

Failure evidence records the exact result for every image.

## R2 Blender fail-closed execution

R2 invokes Blender with `--python-exit-code 23`, so Python exceptions no longer masquerade as a
successful process exit.

R2 also creates a Blender World when `read_factory_settings(use_empty=True)` leaves `scene.world`
unset before rendering.

Future Blender failures surface stdout/stderr tails directly in the Phoenix exception and failure evidence.

## R3 Blender 5.2 render-engine compatibility

The Blender 5.2 runtime on the Phoenix workstation exposes EEVEE as `BLENDER_EEVEE`.
The previous script requested `BLENDER_EEVEE_NEXT`, which caused a Python exception before rendering.

R3 inspects Blender's actual `RenderSettings.engine` enum at runtime:
1. use `BLENDER_EEVEE` when exposed;
2. otherwise use `BLENDER_EEVEE_NEXT`;
3. otherwise fail explicitly and include the available engine identifiers.

This removes a hardcoded Blender-version assumption.

## R4 GPU-independent headless rendering

The Phoenix workstation's EEVEE path failed because the active graphics stack did not expose
`GL_ARB_shader_draw_parameters`; Blender subsequently raised an access violation while compiling EEVEE shaders.

R4 removes GPU/OpenGL EEVEE dependency from the autonomous render path.

Phoenix now uses:
- Blender Cycles;
- CPU render device;
- 8 samples;
- adaptive sampling;
- no denoising requirement.

This keeps IFC-to-render generation deterministic and suitable for unattended Phoenix execution even where
EEVEE-compatible GPU capabilities are unavailable.

EEVEE may still be used later as an optional interactive/render acceleration mode after a separate GPU capability gate.

## R5 Cycles add-on bootstrap

In the workstation's clean `--factory-startup` Blender session, the initial render-engine enum exposed
only `BLENDER_EEVEE`. R5 therefore explicitly enables the bundled `cycles` add-on before selecting
the `CYCLES` engine.

The order is now:

1. start Blender headless with factory startup;
2. enable `cycles`;
3. verify that `CYCLES` is registered;
4. select `CYCLES`;
5. force CPU device;
6. run the IFC-derived presentation render.

A dedicated bootstrap smoke executes this sequence before the complete PAT-002 rendering regression.

## R6 authoritative Blender CLI Cycles bootstrap

Direct workstation diagnostics proved:

- `blender --background --factory-startup -E help` lists `CYCLES`;
- `blender --background --factory-startup -E CYCLES ...` yields
  `bpy.context.scene.render.engine == "CYCLES"`;
- the Python enum list may still report only `BLENDER_EEVEE`.

Therefore R6 treats the actual runtime scene engine as authority and no longer treats
`RenderSettings.engine.enum_items` as the Cycles capability source.

Both the smoke test and full render now invoke Blender with `-E CYCLES`, then force
`scene.cycles.device = "CPU"`.

This matches the proven behavior of the installed Blender 5.2 runtime.

## R7 preserve CLI-selected Cycles engine

R6 proved that Blender starts correctly with `-E CYCLES`, but the render script immediately called
`bpy.ops.wm.read_factory_settings(use_empty=True)`. That second factory reset recreated the scene and
returned the render engine to `BLENDER_EEVEE`.

R7 removes the in-script reset.

The authoritative Blender startup sequence is now:

1. `--background`;
2. `--factory-startup`;
3. `--python-exit-code 23`;
4. `-E CYCLES`;
5. execute the Phoenix render script;
6. verify that `bpy.context.scene.render.engine == "CYCLES"` before OBJ import;
7. force `scene.cycles.device = "CPU"`;
8. render the IFC-derived presentation images.

There is now exactly one factory bootstrap: the Blender command line.

## R8 PNG evidence validator correction

R7 proved that Blender successfully saved all four requested images and produced scene evidence.
The remaining failure was therefore isolated to artifact validation.

The PNG signature check had been generated with escaped backslashes, causing valid PNG files to fail
the magic-byte comparison. R8 uses the canonical PNG header through:

`bytes.fromhex("89504E470D0A1A0A")`

No render-generation behavior changes in R8.

## R9 DE TV regex contract-test correction

R8 completed the real PAT-002 Blender render regression successfully. The remaining failure was isolated
to a Python source-contract test that over-escaped JavaScript regular-expression tokens.

The runtime JavaScript correctly contains:

- `toon\s+`
- `variant\s*b`

The test expected two literal backslashes instead of one. R9 corrects only that test expectation and adds
a regression ensuring the JavaScript regex representation remains correct.
