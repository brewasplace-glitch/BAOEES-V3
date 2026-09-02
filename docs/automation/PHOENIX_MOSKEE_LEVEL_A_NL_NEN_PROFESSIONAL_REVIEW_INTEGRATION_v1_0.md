# PROJECT PHOENIX MOSKEE LEVEL-A NL NEN PROFESSIONAL REVIEW INTEGRATION v1.0

This masterpack extends the existing Level-A and structural v8.0-v8.12 chain. It does not replace CalculiX or OpenSees.

## Production wiring

- Resolves Netherlands jurisdiction from project context or the authoritative Moskee binding.
- Writes the tested NL NEN professional-review candidate action/load basis to the existing v8.2 required-input contract.
- Preserves every unresolved NDP, wind, snow-shape, ULS and Category-C mapping item explicitly.
- Generates an evidence-based Professional Review Package manifest and ZIP from artifacts actually present.
- Missing required outputs remain visible and force `DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW_INCOMPLETE`.
- Starts the authoritative `ArchitecturalOrchestrationRuntime.start(project_file)` entrypoint.
- Tracks the exact returned job ID and log path, waits for its terminal state, and consumes only that job's isolated `structural_session_bridge/workspace`.
- Verifies the bridge result belongs to the started job before packaging any evidence.
- Bootstraps the repository root for direct standalone runner execution and verifies this with a preflight.

## Governance

- `NOT_FOR_CONSTRUCTION`
- `FORMAL_RELEASE=LOCKED`
- `PROFESSIONAL_REVIEW_REQUIRED`
- No automatic professional approval
- No invented norm values or silent Dutch NDP defaults
