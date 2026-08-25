# Project Phoenix Level-A Nonresidential Architecture Route Context Bridge Repair v1.0

## Classification

`REPAIR / EXTEND_ROUTING_ONLY`

## Proven Level-A blocker

The first real Level-A end-to-end run for the Moskee Bunschoten project reached the
Generic Session Adapters but stopped on:

`ARCHITECTURAL_USE_TYPE_REQUIRED`

The selected project binding already declares `NONRESIDENTIAL_REUSE_V1`. The Generic
Session architecture adapter, however, inspected only uploaded JSON models and then fell
through to the residential-only text bootstrap.

## Repair

Before the residential text bootstrap is considered, the architecture adapter now checks
the explicitly selected project binding. If that binding declares
`NONRESIDENTIAL_REUSE_V1`, Phoenix reuses a tracked project-scoped canonical architecture
model and creates a lossless Generic-Session-compatible `levels -> storeys` view.

No mosque-specific architecture generator and no second nonresidential architecture engine
are introduced.

The residential bootstrap remains unchanged. Unknown nonresidential building uses without
an explicit reuse route continue to fail closed with `ARCHITECTURAL_USE_TYPE_REQUIRED`.

## Evidence and safety

The bridge records the selected binding, source model and source SHA-256 in the project
runtime. Derived compatibility objects remain concept candidates.

Automatic professional approval: disabled.

Production release: LOCKED.

FOR CONSTRUCTION: LOCKED.
