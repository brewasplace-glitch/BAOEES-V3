# PROJECT PHOENIX 4.41 — FASE 4 Autonomous Execution Orchestrator + Approval Resume Engine v1.0

Installation baseline: `2e03f18e5b8ef9e18f6cedcc8c840ea547113856`.

FASE 4 converts Phase-3 plans into durable policy-governed runs. READY read-only
steps execute automatically. ESCALATE pauses and creates an HMAC-bound human
approval request. APPROVE/REJECT/DEFER receipts are bound to the exact plan,
step, policy bundle and request nonce, after which execution resumes from the
persisted checkpoint.

DENY cannot be overridden by approval. Approval is never a gateway permit.
Every actual mutation still requires a registered engine and a fresh Phase-2
Universal Autonomy Gateway permit. Interrupted in-progress mutations are never
replayed automatically. Unknown executors fail closed.

Temporal is the primary future durable-runtime adapter candidate (MIT); Prefect
is the fallback Python-native adapter (Apache-2.0). Neither is a hard dependency
in Phase 4 v1.
