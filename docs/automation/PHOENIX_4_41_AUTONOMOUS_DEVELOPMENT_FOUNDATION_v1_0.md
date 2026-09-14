# PROJECT PHOENIX 4.41 — Autonomous Development Foundation v1.0

## Baseline

Branch: `project-phoenix`
Required HEAD: `e897e302431d09e85341dcb9dc5279671bd0f61a`

## Purpose

Foundation v1.0 establishes the governed autonomous-development loop:

`OBSERVE -> DETECT -> PRIORITIZE -> OPEN-SOURCE SCOUT -> PLAN -> RISK -> GATE -> EVIDENCE -> LEARN`

The execution phase exists in the plan schema but is locked by default.

## Components

1. Autonomy Policy
2. Risk Classifier
3. Capability Registry
4. Backlog Generator
5. Task Planner
6. Safe Worktree Manager
7. Open-Source Scout
8. Test/Evidence Gate
9. Auto-Repair FSM
10. Learning Event Store
11. Autonomous Cycle Runner
12. Runtime HTML Dashboard

## Safety model

v1.0 is dry-run-first.

- LOW-risk mutation execution is implemented as a policy concept but locked.
- MEDIUM/HIGH require later explicit governance.
- CRITICAL is blocked.
- protected Phoenix paths are never LOW.
- dry-run never mutates the repository.
- no force-push, reset --hard, or destructive repository cleanup is used.
- learning/runtime evidence is written under `%LOCALAPPDATA%\PROJECT-PHOENIX\autonomy`,
  not into the repository worktree.

## Open-source-first assessment

Primary orchestration candidate: LangGraph (MIT).
Fallback orchestration candidate: Prefect (Apache-2.0).
Primary Git library candidate: GitPython (BSD-3-Clause).
Fallback Git implementation: Dulwich (Apache-2.0 OR GPL-2.0-or-later).

Foundation v1.0 does not install third-party packages automatically. It records
and exposes adapter candidates while Phoenix-specific governance remains
dependency-light and deterministic.

## Next activation

After a successful real dry-run on the committed baseline, the next build may
unlock **LOW-risk auto execution only**, still behind exact-scope, test,
evidence, worktree-isolation and remote-race gates.


## FIX R2 — Git porcelain preservation

A real dry-run exposed a repository-status parsing defect. `git status --porcelain=v1`
uses leading whitespace as part of the XY status field. The Git wrapper previously
called `.strip()` on complete stdout, which removed the leading status byte from the
first record only.

FIX R2 changes the wrapper to remove newline terminators only. Leading porcelain
status bytes are preserved exactly. A real temporary Git repository regression test
verifies that a first record ` M tracked.txt` remains byte-for-byte intact and
normalizes to `tracked.txt`.

## FIX R3 — staged recovery and whitespace QA

FIX R2 proved the real dry-run and Git porcelain handling, then correctly stopped
at `git diff --cached --check` because the new Markdown file contained trailing
spaces.

FIX R3 adds:
- safe recovery from both staged and unstaged interrupted installer state;
- payload-wide trailing-whitespace normalization at package build time;
- an explicit pre-stage whitespace scan over every installed text target;
- the existing staged `git diff --cached --check` remains the final whitespace gate.
