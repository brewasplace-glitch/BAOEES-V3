# PROJECT PHOENIX 4.41 — Phase 10 v1.0

## Bounded Autonomous Repository Improvement Cycle
### Isolated Worktree Mutation + Test-Gated Governed Promotion

Phase 10 advances the proven Phase-9 LOW-risk read-only runtime into a bounded
repository-improvement cycle. Candidate changes are created only in a linked
Git worktree outside the main repository, classified against an exact path
policy, replayed deterministically and bound to a hardened runtime proof.

## Lanes

- `LOW_NON_EXECUTABLE`: documentation and evidence within the pre-existing
  LOW-risk roots. Eligible for backup-gated fast-forward promotion.
- `LOW_EXECUTABLE_APPROVAL_BOUND`: generated adapter source with companion
  generated tests or documentation. It always pauses for an explicit HMAC- and
  SHA-bound approval before any mainline promotion.

## Proof chain

`observe -> classify LOW -> impact lock -> verified backup -> external worktree
-> gateway-bound candidate mutation -> protected-path gate -> binary patch ->
deterministic replay -> accepted isolation proof -> signed attestation ->
fast-forward eligible or approval required`

## Hard boundaries

- One cycle per invocation.
- At most three unique repair attempts; identical failed patch retry is denied.
- Candidate worktree must be outside the main repository.
- Main worktree remains clean and unchanged during candidate verification.
- Deletes, renames, copies, symlinks, junctions and path escapes are denied.
- Policies, registries, CI/CD, dependencies, credentials, backup logic and the
  Phase-10 governor itself are protected.
- Sandbox networking remains disabled.
- Promotion is fast-forward only after verified backup and remote-race guard.
- Force-push and history rewrite are denied.
- Automatic policy/registry changes and automatic engine activation are denied.
- MEDIUM escalates; HIGH and CRITICAL remain denied.
- Professional approval and for-construction release remain denied.

## Honest Phase-10 boundary

Installation proves the repository lifecycle against a synthetic temporary Git
repository and executes the exact candidate patch identity inside the accepted
security boundary. The real Phoenix repository is changed only by the governed
Phase-10 installer scope. Executable Lane-B candidates are staged for review;
they are never promoted automatically.

## Components

- `configs/phoenix/repository_improvement_cycle_policy_v1.json`
- `configs/phoenix/protected_repository_paths_v1.json`
- `configs/phoenix/repository_cycle_attestation_v1.schema.json`
- `phoenix/autonomy/change_classifier.py`
- `phoenix/autonomy/worktree_guard.py`
- `phoenix/autonomy/repository_cycle.py`
- `runners/PROJECT_PHOENIX_4_41_bounded_repository_improvement_cycle_v1.py`
- `tests/automation/test_phoenix_441_bounded_repository_improvement_cycle_v1.py`

## Installation governance

The all-in-one installer is bound to clean, origin-synced branch
`project-phoenix` at Phase-9 commit
`9cda9eca36d08049352c8f952a056ca020094e6d`. Before repository mutation it
requires package integrity, an accepted live isolation provider and a verified
external full backup. It then runs package regressions, installs only the exact
allowlist, repeats installed regressions and live proof, validates the diff,
commits, applies the remote-race guard, pushes normally and records a clean
baseline receipt.
