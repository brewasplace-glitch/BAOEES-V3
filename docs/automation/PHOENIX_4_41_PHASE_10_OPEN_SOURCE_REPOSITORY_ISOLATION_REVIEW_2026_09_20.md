# PROJECT PHOENIX 4.41 — Phase 10 Open-Source Review

Date: 2026-09-20
Decision: accepted with bounded controls

## Primary — Git CLI

Native Git worktrees are selected for isolated candidate state. Git documents
linked worktrees as separate working trees attached to one repository and
supports detached throwaway worktrees for experimental work. Native
`git merge --ff-only` remains the only accepted integration mechanism.

Upstream: https://git-scm.com/docs/git-worktree
Merge reference: https://git-scm.com/docs/git-merge
License: GPL-2.0-only

## Fallback — GitPython

GitPython remains an inspection/integration fallback already recognized by
Phoenix. It may not replace native ancestry verification, remote-race checks,
fast-forward enforcement or push verification.

Upstream: https://github.com/gitpython-developers/GitPython
Documentation: https://gitpython.readthedocs.io/en/stable/
License: BSD-3-Clause

## Build-versus-adopt decision

Phoenix will not implement a Git object database, merge algorithm, credential
manager or repository transport. Phase 10 adds only Phoenix-specific policy,
classification, gateway, evidence and orchestration around the accepted native
Git mechanisms.

## Security acceptance conditions

- exact clean/synced baseline;
- external candidate worktree;
- protected-path and symlink/junction denial;
- deterministic binary patch replay;
- hardened runtime proof with networking disabled;
- verified backup before promotion;
- remote-race guard;
- fast-forward-only merge;
- normal non-force push;
- executable-source approval pause;
- automatic engine activation forbidden.
