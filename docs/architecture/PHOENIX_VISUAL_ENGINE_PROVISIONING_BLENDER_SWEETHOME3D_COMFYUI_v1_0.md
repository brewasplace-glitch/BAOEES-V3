# PROJECT PHOENIX VISUAL ENGINE PROVISIONING + BLENDER/SWEET HOME 3D/COMFYUI INTEGRATION v1.0

## Purpose

Provision missing open-source visual engines on Windows and connect them to the existing Phoenix
Open-Source Architectural Visual Design Stack.

Required repository baseline:

`d61bc1df9e77aa0eec4cb2c5f63c8ec76087db6f`

## Provisioning policy

### Blender

Blender is REQUIRED for this pack because Phoenix already contains a deterministic:

`IFC -> IfcOpenShell geometry -> OBJ -> Blender -> PNG`

pipeline.

If Blender is absent, the installer attempts installation through Windows Package Manager using:

`BlenderFoundation.Blender`

After provisioning, Phoenix must rediscover Blender and a real background/headless Blender process
must write smoke evidence successfully. The repository is not mutated until Blender has passed
post-install discovery.

### Sweet Home 3D

Sweet Home 3D is OPTIONAL_INTERIOR.

If absent, the installer attempts:

`eTeks.SweetHome3D`

Failure to provision Sweet Home 3D does not invalidate the Phoenix core or Blender render path.

Sweet Home 3D is intended for:
- furniture/layout exploration;
- interior design review;
- interior visualization.

IFC remains the authoritative building geometry.

### ComfyUI Desktop

ComfyUI is OPTIONAL_AI_VISUAL.

If absent, the installer attempts:

`Comfy.ComfyUI-Desktop`

The Phoenix integration distinguishes:
- ComfyUI API/home actually available; and
- Comfy Desktop package installed but not yet initialized.

The latter may require a first user launch to create/configure an instance before the local API is available.

No checkpoint, diffusion model, LoRA, VAE or other model weight is automatically downloaded by this pack.

## AI geometry rule

ComfyUI outputs are concept/presentation artifacts.

They may not silently replace:
- IFC walls;
- spaces;
- windows;
- doors;
- roof;
- site geometry;
- structural geometry.

A later Phoenix QA/promote workflow is required before any AI-derived geometric design change becomes authoritative.

## Blender verification

The installer runs Blender with:
- `--background`
- `--factory-startup`
- `--python-expr`

The process must successfully create a Phoenix smoke artifact in an isolated temporary directory.

No GUI is opened during this verification.

## Package-management behavior

Provisioning uses Windows Package Manager (`winget`) with:
- exact package identifier;
- source/package agreement acceptance;
- silent installation;
- disabled interactivity.

Blender provisioning is required and fail-closed.

Sweet Home 3D and ComfyUI provisioning are optional and fail-soft with explicit warnings.

## Repository behavior

Only after third-party provisioning is complete does the installer mutate the Phoenix repository.

It adds:
- visual-engine provisioning helper;
- provisioning policy;
- central registry provisioning metadata;
- Comfy Desktop installed-state handling;
- regression tests;
- this architecture document.

All existing visual, engine-discovery and IFC foundation regressions are rerun.

## Commit/push safety

The installer:
1. validates exact baseline and clean tree;
2. provisions applications before repo mutation;
3. applies only allow-listed repository changes;
4. runs syntax, smoke and regression tests;
5. runs `git diff --check`;
6. commits;
7. verifies clean tree before push;
8. pushes;
9. verifies local/remote equality;
10. never destructively resets an already committed/pushed result.

## Release status

IFC remains authoritative geometry.

Professional review remains required.

Production release remains LOCKED.
