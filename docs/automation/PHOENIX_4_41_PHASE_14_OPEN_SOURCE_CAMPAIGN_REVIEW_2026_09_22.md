# PROJECT PHOENIX 4.41 — Phase 14 Open-Source Campaign Review

## Selected

- Python `heapq` remains the deterministic priority scheduler.
- Python `sqlite3` provides dependency-free transactional resume checkpoints.
- SQLite atomic commit semantics align with the fail-closed crash boundary.

## Considered but not admitted

- APScheduler supports persistent job stores, but Phase 14 is invocation-bound
  and does not admit a scheduler daemon or automatic dependency installation.
- Prefect supports durable retries and workflow state, but its orchestration
  runtime exceeds the offline, dependency-denied Phase-14 boundary.

The review does not authorize automatic installation or engine activation.
