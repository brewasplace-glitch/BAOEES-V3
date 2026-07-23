# Runtime Architecture

The BB8 Runtime Orchestrator coordinates engines, dependencies, retries,
parallel tasks, lifecycle events and runtime evidence.

All future engines must:

- declare capabilities and dependencies;
- publish lifecycle events;
- write durable results to the Digital Twin;
- report failures without committing partial project state.
