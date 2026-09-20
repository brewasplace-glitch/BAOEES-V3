# PROJECT PHOENIX 4.41 — Phase 11 v1.0

## Bounded Multi-Task DAG Orchestration

Phase 11 adds deterministic coordination of specialized, read-only agents. A
validated directed acyclic graph releases only dependency-ready tasks and runs
at most three independent tasks concurrently. Every result is merged in stable
task-id order and bound to a signed attestation.

Hard boundaries:

- LOW risk only;
- at most 12 tasks and three workers;
- read-only specialized agents only;
- no arbitrary shell, network access or repository mutation;
- unknown agents, actions, dependencies and cycles fail closed;
- mutating tasks require a serial governed handoff and never enter the pool;
- live proof must cross the accepted Phase-9 security boundary twice;
- no automatic policy, registry or engine activation.

The primary scheduler is Python `graphlib.TopologicalSorter`. Parallel batches
use a bounded `ThreadPoolExecutor`; NetworkX is an optional inspection fallback
and is never required at runtime.
