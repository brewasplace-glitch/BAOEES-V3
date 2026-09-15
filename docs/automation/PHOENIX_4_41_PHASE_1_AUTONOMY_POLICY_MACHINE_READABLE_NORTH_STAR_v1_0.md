# PROJECT PHOENIX 4.41 — FASE 1 — AUTONOMY POLICY + MACHINE-READABLE NORTH STAR v1.0

Installation baseline: `96862375b84934bab99ef0f89f105cc24aa464b3`.

## North Star

The North Star defines what PHOENIX is optimizing for and which invariants may
never be traded away. It is machine-readable, versioned and cryptographically
bound to Autonomy Policy v2.

Core hierarchy: safety/law → truth/evidence → professional authority → explicit
human constraints/approvals → project objectives → quality/reproducibility →
cost/time optimization.

## Four effects

- `ALLOW`: autonomous execution is authorized immediately.
- `ALLOW_WITH_GATES`: autonomous execution is authorized only when every named gate is satisfied.
- `ESCALATE`: PHOENIX must obtain an explicit strategic/human decision before proceeding.
- `DENY`: PHOENIX must not execute the action.

Unknown mutation fails closed to `DENY`. Unknown read-only authority escalates.

## Central gateway rule

Every autonomous mutation must obtain a decision from the same central
`AutonomyDecisionEngine`. Every decision records the North Star version, policy
version, bundle SHA256, matched rule, required gates, missing gates and final
authorization state in JSONL evidence.

The existing LOW-risk self-improvement runner is integrated with the central
engine. Its generated-document mutation is allowed only when the full pre-mutation
gate set is present. Source-code self-modification remains `ESCALATE` and
MEDIUM/HIGH/CRITICAL autonomous mutation is not opened by this phase.

## Hard denials

Fabricated evidence, force push/history rewrite, governance-gate bypass, secret
exfiltration, professional-approval impersonation and unapproved
for-construction/production release are non-negotiable `DENY` outcomes.

## Open-source-first

OPA is the primary future policy-engine adapter target. Cedar is the fallback
adapter target. FASE 1 keeps a small deterministic bootstrap evaluator active so
that the authority contract is vendor-neutral and does not depend on installing
an external executable before the contract itself is established.
