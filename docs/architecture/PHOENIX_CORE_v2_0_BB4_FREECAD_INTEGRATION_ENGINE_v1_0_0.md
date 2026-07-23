# Phoenix Core v2.0 — BB4 FreeCAD Integration Engine v1.0.0

## Purpose

BB4 upgrades the BB3 FreeCAD foundation adapter to an operational,
policy-controlled integration engine using FreeCADCmd and a JSON file protocol.

## Delivered

- FreeCADCmd executable and version detection;
- controlled subprocess execution without shell invocation;
- bounded request timeouts;
- parametrical creation of boxes, cylinders and spheres;
- import to FCStd;
- export to STEP, IGES, BREP, STL and OBJ families;
- document inspection;
- geometry validity checks;
- opt-in custom Python macro execution;
- atomic job and result files;
- output-file SHA-256 evidence;
- adapter audit evidence and Digital Twin write-back compatibility.

## Security and operational boundary

Custom FreeCAD macros are disabled by default and require the adapter context
setting `allow_custom_freecad_macros: true`. BB4 validates file formats and uses
argument-array subprocess execution with `shell=False`.

The automated tests use a simulated FreeCADCmd runner. Real FreeCAD execution
is performed only when FreeCADCmd is installed on the target machine.

## Progress

Phoenix Core v2.0 overall progress after BB4: **25%**.
