# PROJECT PHOENIX — MOSKEE BUNSCHOTEN REAL-PROJECT E2E BLOCKER REPAIR v1.1

## Bound baseline
`project-phoenix` @ `c6c5f875a26fe9a882d1cedcd7ff623a4a34988b`

## Confirmed blockers from real E2E evidence
1. Playwright video evidence failed because its isolated browser cache did not contain
   the required Playwright FFmpeg binary.
2. The canonical file `configs/projects/moskee_bunschoten.json` was not launchable through the official
   architectural project catalog. That catalog intentionally requires a real
   project identity and excludes metadata-only/no-identity JSON.

## Repair
- Install Playwright's FFmpeg component into the existing isolated browser cache.
- Create `configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json` by cloning the canonical Moskee Bunschoten JSON and adding a
  unique top-level execution identity `MOSKEE-BUNSCHOTEN-E2E-REAL-001`.
- Preserve a metadata pointer back to the canonical project file.
- Bind the existing real-project E2E runner to this execution binding.
- Prove the binding is visible in `ArchitecturalOrchestrationRuntime.project_catalog()`
  and accepted by `plan()` before commit.
- Re-run the real E2E automatically after commit/push.

No official start-screen core or DE TV core file is modified.

A later runtime `BLOCKED_*` result remains valid evidence of the next real E2E blocker.

Production and FOR CONSTRUCTION remain locked.
