# BB12 QGIS Integration Engine Specification v1.0

## Required capabilities

1. QGIS runtime discovery
2. Offline-safe operation
3. GIS project and layer models
4. CRS and extent validation
5. GeoJSON read/write validation
6. QGIS `.qgs` project generation
7. Deterministic GIS manifest with SHA-256 evidence
8. Basic spatial primitives
9. Digital Twin bridge
10. Knowledge Graph bridge
11. Provider-neutral service catalog
12. Automated tests and self-test

## Acceptance criteria

- Python compile validation passes
- All BB12 unit tests pass
- BB12 self-test passes
- `git diff --check` passes
- Commit and push occur only after all checks succeed
- Final repository state is clean
