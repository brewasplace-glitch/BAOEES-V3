# PROJECT PHOENIX — REAL-PROJECT E2E RUNTIME DISCOVERY v1.1

Bound baseline: `project-phoenix` @ `54b2ac361c2bb49c4eb43fe129ea38fb516dad7e`.

The v1.0 harness succeeded, but `NOT_DETECTED` only described its narrow discovery scope.
v1.1 expands discovery without installing anything: PATH, bounded repository locations,
common Windows install locations, configured executable paths, and versioned CalculiX
names such as `ccx_2.22.exe`.

Playwright remains primary browser evidence (Apache-2.0), Selenium WebDriver fallback
(Apache-2.0). FreeCAD remains the CAD/BIM open-source engine, Blender the render/visual
engine, and CalculiX the structural solver. No project is silently selected.

Canonical real-project roots are surfaced separately from the 43 config files:
`bruynzeel_waterfront.json`, `moskee_bunschoten.json`, and `plutostraat.json`.
PAT-001 is surfaced separately as a pilot/validation candidate.

Production and FOR CONSTRUCTION remain locked.
