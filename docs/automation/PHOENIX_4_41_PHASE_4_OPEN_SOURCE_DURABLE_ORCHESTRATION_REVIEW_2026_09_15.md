# PHOENIX 4.41 — Phase 4 Open-Source Durable Orchestration Review — 2026-09-15

## Temporal — primary future durable runtime adapter

Repository: https://github.com/temporalio/temporal
License: MIT
Fit: durable workflow execution, recovery/retries, long-running waits and
signal-based human-in-the-loop resume.

## Prefect — fallback Python-native adapter

Repository: https://github.com/PrefectHQ/prefect
License: Apache-2.0
Reviewed Python requirement: >=3.10,<3.15
Fit: Python workflow orchestration with documented pause/suspend flow patterns
that accept user input and later resume.

## Phase 4 v1 decision

Keep Phoenix's authority boundary vendor-neutral. Use local HMAC-protected
checkpoints and approval artifacts now; preserve Temporal and Prefect as
replaceable future durable-runtime adapters.
