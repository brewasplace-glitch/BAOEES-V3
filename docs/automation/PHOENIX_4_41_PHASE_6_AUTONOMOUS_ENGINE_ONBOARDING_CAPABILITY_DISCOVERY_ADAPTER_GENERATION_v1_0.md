# PROJECT PHOENIX 4.41 — FASE 6 Autonomous Engine Onboarding + Capability Discovery + Adapter Generation v1.0

Installation baseline: `c0601868316171929567382029bd470640abd880`.

FASE 6 adds a bounded onboarding pipeline for future Phoenix engines:

`static discovery -> candidate manifest -> semantic validation -> capability
profile -> Phase-5 adapter admission -> policy coverage probe -> adapter scaffold
staging -> signed onboarding proposal`

Discovery is deliberately non-executing. Repository manifests are parsed as
JSON and Python entry points are enumerated as metadata; candidate plugin code
is not imported during discovery.

Generated adapter code is written only to the local Phase-6 runtime staging
area. It is not written into the repository and is never activated
automatically. Repository activation remains a governed backup-first change.

Mutating engines require `gateway_required=true`, explicit mutation scope and
gateway-bound adapters. Unknown actions remain denied by central policy until an
explicit governed policy change permits them.

Open-source-first: pluggy is the primary future live hook provider (MIT);
stevedore is the fallback entry-point/driver discovery provider (Apache-2.0).
Neither is a hard runtime dependency in v1.
