# PROJECT PHOENIX 4.41 — PHASE 8 v1.0
## Autonomous Adapter Implementation Synthesis + Isolated Verification + Governed Promotion

Status: ACTIVE — STATIC-ONLY, FAIL-CLOSED

Phase 8 is bound to predecessor baseline
`7f96229cb51db91c7e3dbca6681a2fae7c9dce27`.

## Delivered chain

`signed Phase-6 proposal -> deterministic read-only implementation synthesis -> Phase-7 AST/contract validation -> exact byte replay -> signed non-execution attestation -> explicit SHA-bound Phase-7 review handoff`

## Safety decision

No reviewed Windows-compatible isolation provider is accepted as a PHOENIX
security boundary in this release. Generated candidate code is therefore never
executed during Phase-8 verification. The isolation provider interface exists,
but its active implementation fails closed.

## Hard invariants

- Only signed Phase-6 proposals with PASS admission are accepted.
- Only generated, plan-dispatchable, read-only adapters can be synthesized.
- Mutation-capable adapter synthesis is denied.
- The synthesized source is byte-deterministic and bound to a canonical spec
  digest and source SHA256.
- The existing Phase-7 implementation validator must pass.
- Candidate code is not imported, compiled or executed by Phase 8.
- Network, process spawn and repository writes are denied during verification.
- Attestations and handoffs are HMAC-bound to the local runtime integrity key.
- Governed promotion means review staging only; it does not create a Phase-7
  activation transaction and does not write the repository.
- Automatic engine activation remains forbidden.

## Components

- `configs/phoenix/adapter_synthesis_policy_v1.json`
- `configs/phoenix/adapter_verification_profile_v1.json`
- `configs/phoenix/adapter_runtime_attestation_v1.schema.json`
- `phoenix/autonomy/adapter_synthesis.py`
- `phoenix/autonomy/adapter_verification.py`
- `runners/PROJECT_PHOENIX_4_41_adapter_synthesis_verification_v1.py`
- `tests/automation/test_phoenix_441_adapter_synthesis_verification_v1.py`

## Evidence

Each attestation records the source hash, synthesis spec digest, Phase-7 static
contract report, provider identity and disabled state, network/filesystem/process
policy, empty stdout/stderr hashes, non-run timeout and memory outcomes,
read-only gateway status, deterministic replay result, and final attestation
digest plus HMAC.

## Promotion boundary

A successful attestation is eligible only for an explicitly approved,
SHA-bound `PHASE7_REVIEW_CANDIDATE` handoff. Because isolated execution is
blocked, the handoff remains in runtime staging and is explicitly not eligible
for automatic Phase-7 activation transaction creation.

## Installation governance

The Phase-8 installer requires the exact clean and origin-synced predecessor,
creates and verifies a full external backup, runs package regression tests,
installs only the exact allowlisted scope, reruns installed tests, performs Git
diff and commit-scope gates, commits, applies a remote race guard, pushes with a
normal non-force push, and records the new clean/synced baseline.
