# PROJECT PHOENIX OFFICIAL STARTSCREEN A-E VISUAL STABILITY REPAIR v1.0 R6

Baseline: `5debd33bdd6ccac4bb3bf35bd4ca2788c57f6901` on `project-phoenix`.

## Defect
After successful A-E start-screen integration, the official `/start-v3/` screen visibly flickered.
The new capability client polled `/api/status` every 3 seconds and rebuilt project/capability DOM
even when the returned data had not changed.

## Repair
- no full DOM rebuild when project catalog is unchanged;
- no capability-card rebuild when capability data is unchanged;
- job text changes only when job data changes;
- polling reduced to 6 seconds;
- polling pauses while the tab is hidden;
- refresh uses one recursive timeout, preventing overlapping polls;
- the collapsed autonomous-flow control moves from the top status strip to the bottom-right;
- the panel opens upward;
- no MutationObserver;
- no changes to DE TV player core;
- X-Phoenix-Token and same-origin API contract remain unchanged.

This is a repair revision of the already authorized start-screen integration build.
No new engine or dependency is introduced.

Release remains CONCEPT_ONLY_NOT_FOR_CONSTRUCTION.

## R5 compatibility repair
R4's visual-stability implementation passed all six new stability tests. The installer
then stopped on a previously committed integration regression that checks the exact source
spelling `"X-Phoenix-Token":TOKEN`. R5 preserves the identical secure token behavior and
restores that exact spelling. No server API, DE TV, project-catalog, or orchestration
behavior changes.

## R6 compatibility repair
R5 retained the secure token source contract but the older integration regression also
checks for the exact architectural project-source expression
`status.architectural_orchestration?.projects`.

R6 restores that exact expression inside `applyStatus()` while preserving the R4/R5
anti-flicker design: diff-only DOM updates, 6-second polling, hidden-tab pause,
non-overlapping refreshes, and bottom-right placement. No API, DE TV, security,
project-catalog, or orchestration behavior changes.
