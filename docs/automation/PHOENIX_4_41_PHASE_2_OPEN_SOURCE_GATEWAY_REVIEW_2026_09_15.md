# PHOENIX 4.41 — Phase 2 Open-Source Gateway Review — 2026-09-15

## Primary — Open Policy Agent (OPA)

Repository: https://github.com/open-policy-agent/opa
Role: primary future external policy-decision / policy-enforcement adapter.
Fit: general-purpose unified policy enforcement across a technology stack.
Project status: CNCF graduated.

## Fallback — Cedar

Repository: https://github.com/cedar-policy/cedar
License: Apache-2.0.
Role: fallback future authorization adapter.
Fit: fine-grained authorization, independent policy evaluation and schema
validation.

## Phase 2 decision

The universal Phoenix gateway is implemented as a vendor-neutral contract around
the already active AutonomyDecisionEngine. No external policy runtime is added
to the critical mutation path in v1. OPA and Cedar remain replaceable adapters
behind the same engine registry and one-time permit contract.
