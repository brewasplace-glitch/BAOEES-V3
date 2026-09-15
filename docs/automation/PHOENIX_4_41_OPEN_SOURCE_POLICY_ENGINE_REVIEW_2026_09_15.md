# PHOENIX 4.41 — Open-Source Policy Engine Review — 2026-09-15

## Open Policy Agent (OPA) — primary adapter target

- License: Apache-2.0.
- General-purpose, context-aware policy engine.
- CNCF graduated project.
- Strong fit for unified policy enforcement across PHOENIX modules.
- FASE 1 decision: define the PHOENIX contract in vendor-neutral machine-readable JSON and keep OPA as the primary external adapter target.

## Cedar Policy Language — fallback adapter target

- License: Apache-2.0.
- Purpose-built fine-grained authorization language and engine.
- Supports schema validation and analyzable authorization policy.
- FASE 1 decision: fallback adapter target, particularly useful for formal authorization analysis.

## Bootstrap decision

FASE 1 does not install a new external runtime. It first establishes the exact
North Star and authority contract, a fail-closed reference evaluator, integrity
pins, audit log and regression tests. OPA/Cedar adapters can then be added
without changing policy meaning.
