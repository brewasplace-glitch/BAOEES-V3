# PROJECT PHOENIX TROPICAL RESIDENTIAL REAL 3D DESIGN + DE TV PRESENTATION PIPELINE v1.0

## Status
REAL 3D DESIGN DEVELOPMENT / VISUAL PRESENTATION.
CONCEPT ONLY — NOT FOR CONSTRUCTION.

## OSS-first decision — 2026-08-19
Primary 3D renderer: **Blender**, executed in background mode through its Python API.
Blender is GPL and supports background/command-line rendering and scripted `.blend` creation.

BIM/CAD refinement: **FreeCAD 1.1.x**, LGPL-2.1-or-later.
The bridge now uses FreeCAD's documented `--pass` separator so Phoenix JSON/output arguments are
passed to the script rather than interpreted as files that FreeCAD itself should open.

Browser 3D fallback reviewed: **three.js**, MIT.
Decision: do not add it in this build. DE TV's existing local sidecar player is already live-proven,
and its single-visual-authority block is closed. This build therefore integrates by producing the
four canonical media files already consumed by DE TV instead of modifying the player architecture.

## 3D content
For each A-E tropical design variant Phoenix now builds and renders:
- slabs and real wall segments;
- visible door/window openings and fillings;
- tropical rain/solar shading;
- a covered veranda and columns;
- strategy-dependent gable, hip or shed roof geometry;
- variant-specific material palette;
- front, rear, bird's-eye and interior-cutaway cameras;
- camera-fixed variant labels.

## Blender headless rendering — R6
The validated Windows host reached Blender 5.2 successfully but EEVEE's GPU shader path failed
because `GL_ARB_shader_draw_parameters` was unavailable. Phoenix therefore uses **Cycles CPU** as
the mandatory automated/headless render path.

Runtime policy:
- render engine: `CYCLES`;
- render device: `CPU`;
- quick installer smoke: 8 samples at 400×267;
- normal Phoenix render: 48 samples at 1280×720;
- each variant must print runtime evidence for `CYCLES` + `CPU`;
- each variant must produce four PNG views and one `.blend`.

This keeps Blender as the primary open-source 3D renderer while removing the dependency on the
host's OpenGL shader-extension support for unattended Phoenix rendering.

## DE TV integration without reopening the blocker
DE TV already consumes these canonical paths:

`projects/runtime/<PROJECT>/results/generated_visual_media/blender_presentation/`

and these filenames:
1. `phoenix_exterior_front.png`
2. `phoenix_exterior_rear.png`
3. `phoenix_bird_view.png`
4. `phoenix_interior_cutaway.png`

This pipeline writes each canonical `.png` as a standards-based **animated PNG (APNG)** containing
five frames in the order A, B, C, D, E. Consequently the existing DE TV sidecar and its Prev / Next /
Presentation controls remain unchanged, while every displayed view automatically cycles the five
tropical residential variants.

Individual high-quality variant PNGs and `.blend` files are retained separately under
`generated_visual_media/tropical_residential_variants/variant_A..E/`.

## FreeCAD headless execution — R5
Phoenix uses the Python interpreter shipped in the detected FreeCAD `bin` directory as the primary
Windows headless route:

`<FreeCAD bin>/python.exe phoenix_freecad_handoff.py <layout.json> <output.FCStd>`

This avoids the `.py` command-line loader inconsistency observed in current FreeCAD 1.1.x builds
while keeping the exact FreeCAD Python/C++ binary environment. `FreeCADCmd` remains a fallback.

Neither route is accepted on exit code alone. Phoenix also requires the explicit
`PHOENIX_FREECAD_HANDOFF_OK` completion marker and a non-empty FCStd output.


## Release governance
- PROFESSIONAL APPROVAL = NOT AUTOMATIC
- CODE COMPLIANCE = NOT AUTOMATIC
- PRODUCTION = LOCKED
- FOR-CONSTRUCTION = LOCKED
