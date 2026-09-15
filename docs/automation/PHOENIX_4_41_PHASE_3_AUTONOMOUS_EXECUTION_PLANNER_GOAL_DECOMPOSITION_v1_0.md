# PROJECT PHOENIX 4.41 — FASE 3 Autonomous Execution Planner + Goal Decomposition v1.0

Installation baseline: `d8de9e4e4cc5ed19c7e690945152143b11b427d2`.

## Purpose

FASE 3 gives Phoenix a bounded machine-readable planning layer:

`goal -> recursive decomposition -> dependency DAG -> policy decision per step ->
execution readiness -> execution tickets -> existing Universal Autonomy Gateway`

The planner does **not** bypass or replace FASE 1/2 governance. It cannot turn a
policy `ESCALATE` or `DENY` into execution permission.

## Goal contract

Goals use `PHOENIX_GOAL_SPEC_V1` with a stable goal id, objective, goal type,
domain, success criteria, constraints, currently satisfied gates, context and
optional recursive subgoals.

## Plan contract

Plans use `PHOENIX_EXECUTION_PLAN_V1`. Every step records:

- action, domain and risk;
- target engine;
- dependencies;
- paths and proposed gates;
- central policy effect/rule;
- required and missing gates;
- gateway requirement;
- exact policy-bundle SHA.

Plan states are `READY`, `GATED`, `HUMAN_DECISION_REQUIRED` or `BLOCKED`.

## Execution boundary

An execution ticket is **not** a mutation permit. Any actual mutating engine must
still obtain and consume a one-time FASE-2 Universal Autonomy Gateway permit at
the mutation boundary.

## Bounds

Planning is fail-closed and bounded by maximum recursive depth, subgoal fan-out,
step count and dependency count. Cyclic plans are rejected.

## Open-source-first

Primary optional DAG adapter: NetworkX (BSD-3-Clause). Its current project
metadata reviewed on 2026-09-15 requires Python >=3.12 and excludes 3.14.1.

Richer future symbolic/HTN adapter: AIPlan4EU Unified Planning (Apache-2.0),
which exposes planner-independent modeling, hierarchical planning and
scheduling features.

v1 does not require either dependency: it has a deterministic native Kahn DAG
fallback and will use NetworkX when already installed.
