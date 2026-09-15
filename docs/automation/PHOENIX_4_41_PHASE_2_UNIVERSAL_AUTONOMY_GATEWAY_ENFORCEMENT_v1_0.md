# PROJECT PHOENIX 4.41 — FASE 2 Universal Autonomy Gateway Enforcement v1.0

Installation baseline: `3911c31a0b5d62e37ee38bf1365dd1e6f67287e6`.

## Scope

FASE 2 applies the mutation gateway to **all current and future mutation-capable
Phoenix engines**. A future engine is not trusted by naming convention or by
location in the repository. It must first be explicitly registered and must
declare its permitted actions, domains and mutation scope.

The default for an unregistered future engine is `DENY`.

## Mutation chain

`engine intent -> engine registry -> central AutonomyDecisionEngine ->
one-time gateway permit -> exact engine/action/path binding -> permit consume ->
mutation -> evidence/audit`

A policy decision alone is no longer sufficient for a mutation-capable engine.
The actual mutator must consume a valid gateway permit immediately before the
mutation boundary.

## Permit invariants

- one-time use;
- bounded TTL;
- exact engine binding;
- exact action binding;
- exact path binding;
- policy-bundle binding;
- decision binding;
- issue + consume audit events;
- permits from a foreign gateway process are invalid.

## Future-engine admission

Every future mutation-capable engine must be registered in
`engine_registry_v1.json`. Registration changes the autonomy boundary and
therefore remains an `ESCALATE` operation.

Unknown future engines fail closed even when their requested action would
otherwise be LOW-risk.

## Current autonomy mutators

FASE 2 makes the current LOW-risk executor and mainline promoter permit-aware.
Installed policy requires a gateway permit for both.

## Open-source-first

Open Policy Agent remains the primary external policy-engine adapter candidate:
general-purpose policy enforcement and CNCF graduated. Cedar remains the
fallback: an Apache-2.0 fine-grained authorization engine with schema validation.
The PHOENIX gateway contract remains vendor-neutral; neither runtime is required
for this local v1 enforcement layer.
