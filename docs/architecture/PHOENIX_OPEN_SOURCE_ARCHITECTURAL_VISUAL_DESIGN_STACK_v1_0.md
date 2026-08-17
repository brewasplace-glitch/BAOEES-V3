# PROJECT PHOENIX OPEN-SOURCE ARCHITECTURAL VISUAL DESIGN STACK v1.0

## Purpose

Add an open-source visual-design layer without replacing IFC as the authoritative architectural geometry.

## Engines

- Blender: recommended visual core for exterior/interior rendering and animation.
- FreeCAD: optional parametric CAD / STEP / BIM review.
- Sweet Home 3D: optional interior-layout and furniture workflow.
- ComfyUI: optional local AI image/video workflow.

## Geometry authority

IFC remains the source of truth.

Visual and AI outputs are derived presentation or concept artifacts and may not silently replace IFC geometry.

## IFC -> Blender pipeline

The stack contains a deterministic IFC-to-OBJ mesh derivation using IfcOpenShell geometry.

When Blender is available:
1. Phoenix resolves the authoritative IFC.
2. IFC geometry is converted to OBJ.
3. Blender runs headless.
4. Phoenix creates a 1280x720 exterior PNG with ground plane, lighting and camera.
5. Render evidence records the IFC source and Blender execution result.

The initial Blender scene is intentionally conservative. Material libraries, vegetation, furniture catalogues and photorealistic scene intelligence belong to subsequent visual-design packs.

## FreeCAD

The adapter exposes discovery and capability state. It does not make a FreeCAD document authoritative.

## Sweet Home 3D

The adapter exposes interior-design capability discovery. Asset licensing remains separate from application licensing and must be tracked before commercial distribution.

## ComfyUI

The adapter discovers a local installation and/or API at `COMFYUI_URL` (default `http://127.0.0.1:8188`).

AI outputs are not permitted to alter authoritative geometry without a later Phoenix QA/promote step.

## Installer safety improvement

This masterpack changes the post-commit safety pattern:

- all scope/tests/diff checks happen before commit;
- working tree must be clean immediately after commit and before push;
- after a successful push the installer never resets to the old baseline;
- a pushed commit is preserved even if final synchronization verification fails.

This prevents the local/remote divergence seen in earlier foundation installers.

## Release

Professional review remains required.
Production release remains LOCKED.
