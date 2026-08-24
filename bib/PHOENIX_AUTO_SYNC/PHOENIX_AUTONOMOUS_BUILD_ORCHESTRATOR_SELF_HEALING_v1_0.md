# PHOENIX AUTO SYNC — Autonomous Build Orchestrator + Self-Healing v1.0

Phoenix now has a central manifest-driven software-build coordinator.

Core rule:
`DISCOVER -> CLASSIFY -> PREFLIGHT -> EXECUTE -> HEAL -> VERIFY -> SCOPE ->
STAGE -> SECRET_SCAN -> REMOTE_RACE_GUARD -> COMMIT -> PUSH -> FINAL`.

The loop reuses existing Phoenix governance and adds deterministic repair/retry
semantics. Repair actions must be declared in the build manifest. Arbitrary code
repair is not invented by the v1.0 engine.

Open-source candidates reviewed:
- Prefect — Apache-2.0 — primary future orchestration backend candidate.
- Dagster — Apache-2.0 — fallback future orchestration backend candidate.

Neither is mandatory in v1.0 because Phoenix already owns repo-specific
governance and the standard-library implementation keeps the build loop local,
deterministic and dependency-light.

The future Autonomous Development Queue must create validated build manifests
and hand them to this orchestrator rather than duplicating execution logic.
