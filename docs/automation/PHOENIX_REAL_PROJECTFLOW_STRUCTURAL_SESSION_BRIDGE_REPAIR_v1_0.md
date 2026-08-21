# PROJECT PHOENIX — Real Projectflow Structural Session Bridge Repair v1.0

## Bound baseline
`project-phoenix` @ `1aaf4505a450598fb0a5ef1452b61c0d10a95bb4`

## Proven root cause
The server already contains both orchestration paths:

1. `ArchitecturalOrchestrationRuntime`, used by the Start-v3 capability registry button;
2. `AutonomousProjectOrchestrator`, used by `/api/project-analysis/start` followed by
   `/api/autonomous/start`.

The Moskee real-project E2E clicks `.phx-cap-run`, which posts only
`project_file` to the architectural route. Therefore the A–E architectural job can pass
without ever executing `structural_engineering`, even though the binding now contains the
five correct structural desired-output tokens.

## Bounded repair
The dedicated architectural runtime remains the authoritative A–E projectflow and keeps its
existing job/status contract. After a successful architectural delivery manifest is verified,
the runtime checks whether the project binding explicitly enables the
`phoenix_structural_capability_activation` route.

When enabled, it:
- derives only the existing requested output tokens that map to `structural_engineering`;
- creates a project-scoped autonomous bridge session for the same project ID;
- reuses the existing `PROJECT_PHOENIX_autonomous_session_orchestrator_v1_0_0.py`;
- lets the existing dependency planner select architecture + digital_twin +
  structural_engineering;
- requires the structural adapter directory and at least one project-scoped `.inp`;
- keeps production and FOR-CONSTRUCTION release locked.

No new structural engine, solver, architectural engine, Blender path, FreeCAD path, or DE TV
core is introduced.

## Runtime success target
The same Moskee E2E must now reach:
- architectural A–E PASS;
- structural session bridge PASS;
- `results/session_adapters/structural_engineering` present;
- `PROJECT_SCOPED_INP_COUNT > 0`;
- real CalculiX execution from the E2E harness;
- clean/synchronized Git + current BIB.
