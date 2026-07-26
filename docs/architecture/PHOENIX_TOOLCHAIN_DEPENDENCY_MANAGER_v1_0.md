# Phoenix Toolchain & Dependency Manager v1.0.0

## Position in the roadmap

This stabilization layer is installed after BB16 and before BB17.

## Purpose

The manager provides one controlled registry and detection layer for external
engineering applications and Python dependencies used by PROJECT-PHOENIX.

## Managed dependencies

- Python
- Git
- IfcOpenShell
- OpenSeesPy
- FreeCAD
- Blender
- CalculiX
- SketchUp
- SCIA Engineer

## v1.0.0 behavior

The manager:

1. detects executables through Phoenix environment variables, PATH and standard
   Windows installation locations;
2. detects Python packages in the active Phoenix runtime;
3. records availability, version, path, source and capability;
4. creates a deterministic JSON report and SHA-256 fingerprint;
5. creates a non-executing installation plan for missing dependencies;
6. distinguishes required core dependencies from optional specialist tools.

## Safety policy

v1.0.0 never downloads or installs external software automatically. Installation
actions remain plans until a later controlled installer wave is explicitly
approved. This avoids unreviewed license acceptance, version drift and changes
to the workstation.

Runtime reports belong under `outputs/runtime/toolchain/` and remain outside Git.

## BB17 entry gate

BB17 may start after:

- this manager is committed and pushed;
- the repository is clean;
- Python and Git are available;
- the toolchain report can be generated reproducibly.

IfcOpenShell may be installed in the following dependency-enablement wave when
it is not yet present in the active Phoenix Python runtime.
