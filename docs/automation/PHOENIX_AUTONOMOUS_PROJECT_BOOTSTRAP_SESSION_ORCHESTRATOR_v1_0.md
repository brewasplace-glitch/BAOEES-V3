# Phoenix Autonomous Project Bootstrap & Session-Driven Orchestrator v1.0

## Purpose
This build closes the first three defects found in the real standalone PAT.

### PAT-DEFECT-001
Autonomous Project Mode no longer asks the user to select a technical workflow.
After `START PROJECTANALYSE`, Phoenix automatically starts the hidden generic
`autonomous_session_orchestrator_v1_0` workflow.

### PAT-DEFECT-002
The autonomous path no longer invokes BB35/Moskee/pilot-specific runners.
The generic session orchestrator explicitly rejects project-specific/pilot runners.

### PAT-DEFECT-003
The full start-screen context is persisted and propagated:
- session id
- project id
- project type
- project mode
- project brief
- selected existing project, if any
- upload batch reference
- desired output selections

## Durable project bootstrap
A new project workspace is created under:

`projects/runtime/<project_id>/`

with:
- `project_manifest.json`
- `inputs/project_analysis_session.json`
- `digital_twin/project_state.json`
- `orchestration/dependency_plan.json`
- `orchestration/progress.json`
- `orchestration/blockers.json`
- `results/result_index.json`

## Capability safety
v1.0 intentionally does **not** fabricate engineering output.

If Phoenix discovers that a desired output requires an engine that exists only
as a legacy pilot runner, or a generic engine exists but does not yet have a
tested Session Adapter, the run ends in the controlled terminal state:

`BLOCKED`

instead of:
- starting the wrong project runner,
- returning false PASSED,
- or silently generating unrelated project results.

Exit code `10` is mapped by the local workflow registry to `BLOCKED`.

## Next PAT expectation
For an Autonomous Project Mode run:
1. user presses START PROJECTANALYSE;
2. no workflow chooser appears;
3. Phoenix automatically creates a project workspace;
4. the generic Session-Driven Orchestrator is started;
5. the job receives `--session-file <current-session>`;
6. dependency plan and blocker/result registers are created;
7. no `BB35_pilot_1` runner is invoked.

The next blockers, if any, will identify the exact generic capability adapters
that still need to be built for full end-to-end autonomous production.

## FIXED R1
The first install attempt correctly stopped before commit/push because regression
tests exposed packaging/integration issues. R1 fixes:
- temp test repos no longer require the autonomy config unless autonomous mode is used;
- explicit PHOENIX-PAT-001 fixture now contains a real line break;
- old v3.0.2 runtime regression expectation is updated from 1.6.0 to 1.7.0;
- Official Start launcher refuses to reuse an already-running stale 1.6.0 runtime.


## FIXED R2
The R1 installer reached 44 tests with only three remaining errors. All three
had the same cause: on Windows the TemporaryDirectory session path was exposed
through an 8.3 short-path alias (`BREWAS~1`) while the repository object used
the long user path. `Path.relative_to()` therefore raised even though this is
only a path-representation issue.

R2 changes the manifest path reference contract:
- prefer a repository-relative session-file reference when Python can prove it;
- otherwise store the resolved absolute session-file reference;
- never abort project bootstrap solely because of Windows path aliasing.

A dedicated regression test now covers this fallback.
