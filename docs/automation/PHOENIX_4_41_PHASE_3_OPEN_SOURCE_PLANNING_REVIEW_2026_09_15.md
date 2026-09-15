# PHOENIX 4.41 — Phase 3 Open-Source Planning Review — 2026-09-15

## NetworkX — primary optional DAG adapter

Repository: https://github.com/networkx/networkx
License: BSD-3-Clause.
Reviewed latest release: 3.6.1.
Current project metadata: Python >=3.12, excluding 3.14.1.
Use in PHOENIX: DAG validation, lexicographic topological ordering and
topological generations when installed.

## Unified Planning — richer future planning adapter

Repository: https://github.com/aiplan4eu/unified-planning
License: Apache-2.0.
Use in PHOENIX: future symbolic planning / hierarchical task network / scheduling
adapter behind the PHOENIX GoalSpec/ExecutionPlan contracts.

## v1 decision

Do not make either package a hard runtime dependency. The Phase-3 plan contract
and policy bindings remain vendor-neutral. A deterministic native Kahn
topological-sort fallback keeps the planner operational without package
installation, while NetworkX is used automatically when already available.
