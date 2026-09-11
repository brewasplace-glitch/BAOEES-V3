# PHOENIX 4.41 — Structural Drawing Open-Source Review

## Primary drawing engine — ezdxf 1.4.4

- purpose: deterministic headless DXF generation and DXF integrity verification;
- license: MIT;
- current 1.4.4 release dated 2026-05-14;
- project metadata requires Python >=3.10 and lists Python 3.14 support;
- Phoenix installs it into an isolated user-local runtime, outside the repository.

## Secondary candidate — FreeCAD

FreeCAD is retained as the preferred later-stage 3D/BIM path. Current stable 1.1.3 is available for 64-bit Windows.
It is not made a dependency of this 2D consolidation stage because deterministic DXF/SVG generation is sufficient here and avoids imposing a full desktop CAD runtime.

## Deterministic fallback

Phoenix also writes standards-based SVG directly with Python's standard library. SVG output is mandatory even when DXF generation succeeds.

No drawing engine converts preliminary structural evidence into a for-construction release.
