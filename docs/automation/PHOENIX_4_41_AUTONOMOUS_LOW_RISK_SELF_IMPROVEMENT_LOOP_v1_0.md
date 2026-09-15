# PROJECT PHOENIX 4.41 — Autonomous LOW-Risk Self-Improvement Loop v1.0

Installation baseline: `4c4179810b511d0550920f71d8d6ac878693e242`.

## Purpose

The loop closes the LOW-risk autonomous chain:

backlog → plan → open-source review → isolated candidate → exact gates →
verified backup → fast-forward-only promotion → BIB/evidence → clean/synced.

## v1 safety boundary

Only generated `.md`, `.txt` and `.json` documentation/evidence inside the
existing LOW-risk allowlist may be changed autonomously. Phoenix source-code
self-modification remains blocked. MEDIUM, HIGH and CRITICAL execution remain
blocked.

Each invocation performs exactly one bounded cycle and stops on the first
failure. A full verified backup of the exact current baseline is mandatory
before promotion.

## Open-source-first review — 2026-09-15

- Prefect is the preferred future scheduling/retry adapter. It is Apache-2.0,
  actively maintained and its current Python project metadata supports
  Python >=3.10,<3.15.
- LangGraph remains the orchestration fallback candidate under MIT, but current
  2026 security advisories require version/security review before activation.
- v1 does not add a new runtime dependency because the existing PHOENIX
  executor, Git worktree isolation, evidence gates and backup-gated promoter
  already implement the required bounded local cycle.

## Promotion

Mainline promotion is allowed only through the already proven
`git merge --ff-only` promoter with a normal non-force push.

## Backup

The installed PowerShell runner creates a new full repository snapshot and
verified `git bundle --all` before every self-improvement cycle.
