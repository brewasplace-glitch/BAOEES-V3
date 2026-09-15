# PROJECT PHOENIX 4.41 — FASE 5 Universal Capability Executor Registry + Engine Action Adapters v1.0

Installation baseline: `23d8fe7d4fd707d8278ca4b2881819ea6d27f910`.

FASE 5 removes hard-coded orchestrator knowledge of individual READY executors.
Phoenix now uses a machine-readable executor registry:

`engine_id + action -> exact registered adapter -> adapter contract -> existing
policy/gateway boundary -> execution`

Every action of every ACTIVE engine must have registry coverage. Plan-dispatch
actions require an executable adapter. Internal gateway-managed actions are also
registered, but are not exposed to plan dispatch.

Future engine actions default to `DENY_NO_REGISTERED_ADAPTER`. An adapter may
never expand the action scope granted to its engine. Mutating adapters must be
gateway-bound.

Built-in plan adapters in v1:

- `builtin.planner.readonly`
- `builtin.lowrisk.plan`
- `builtin.mainline.promoter`

Existing approval, checkpoint, BIB and self-improvement internal actions are
covered by non-plan-dispatch internal descriptors.

The Phase-4 orchestrator now resolves READY steps through
`UniversalCapabilityExecutorRegistry` rather than engine/action conditionals.

Open-source-first review selected pluggy as the primary future external adapter
provider and stevedore as fallback. v1 keeps both optional and introduces no hard
runtime dependency.
