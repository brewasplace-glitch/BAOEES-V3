# PHOENIX 4.41 — Open-Source Orchestration Review — 2026-09-15

## Prefect — primary future adapter

Repository: https://github.com/PrefectHQ/prefect
License: Apache-2.0
Fit: workflow orchestration, retries, scheduling, event automation.
Python compatibility reviewed: current project metadata declares >=3.10,<3.15.
Decision: preferred future scheduling/retry adapter; not required as a runtime
dependency for the v1 single bounded local cycle.

## LangGraph — fallback future adapter

Repository: https://github.com/langchain-ai/langgraph
License: MIT
Fit: stateful workflow/agent graphs and durable state.
Security note: public 2026 advisories exist; activate only after pinned-version
security review.
Decision: fallback adapter, not active in v1.

## v1 implementation decision

Reuse the already proven PHOENIX deterministic governance core, native Git
worktrees, LOW-risk executor, backup runner and `git merge --ff-only` promoter.
This avoids introducing a new dependency where no missing execution primitive
exists while preserving clear open-source integration targets for future
multi-flow scheduling.
