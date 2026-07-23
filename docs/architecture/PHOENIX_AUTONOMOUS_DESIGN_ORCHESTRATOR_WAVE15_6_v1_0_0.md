# Phoenix Autonomous Design Orchestrator — Wave 15.6 v1.0.0

## Purpose

Wave 15.6 coordinates Phoenix engines in a deterministic dependency graph and
maintains one auditable workflow state.

## Core behavior

- validates workflow steps and dependencies;
- rejects duplicate steps and dependency cycles;
- executes registered engines in topological order;
- separates required and optional engines;
- blocks dependent steps after failures;
- supports explicit input and output state keys;
- records SHA-256 evidence per engine output and for the complete workflow;
- retains human approval by default.

## Integration sequence

1. Wave 15.1 — Optimization Core
2. Wave 15.2 — Multi-Material Design
3. Wave 15.3 — Cost & Carbon Optimization
4. Wave 15.4 — Variant Ranking & Decision Intelligence
5. Wave 15.5 — Autonomous Decision Engine
6. Wave 15.6 — Autonomous Design Orchestrator
7. Wave 15.7 — Digital Twin Synchronization

## Safety boundary

The orchestrator coordinates software engines but does not certify technical,
legal, financial, environmental or regulatory compliance.
