# Phoenix Core v2.0 — BB8 Runtime Orchestrator Engine v1.0.0

## Purpose

BB8 introduces the central runtime layer that registers, orders, executes,
monitors and audits Phoenix tasks and engines.

## Delivered capabilities

- dependency-aware task execution;
- parallel execution of independent tasks;
- deterministic priority ordering;
- retry support;
- cancellation support;
- failed-dependency blocking;
- cycle and unknown-dependency detection;
- runtime event bus;
- task lifecycle events;
- engine registry and health checks;
- JSON runtime snapshots;
- SHA-256 runtime evidence;
- CLI self-test and PowerShell runner.

## Runtime model

A task may run only after all declared dependencies have completed
successfully. A failed task blocks its dependants. Independent ready tasks may
run in parallel, subject to the configured worker limit.

## Integration

BB8 is designed as the central execution layer for BB1 through BB7 and all
future Phoenix engines.

## Progress

Phoenix Core v2.0 overall progress after BB8: **56%**.
