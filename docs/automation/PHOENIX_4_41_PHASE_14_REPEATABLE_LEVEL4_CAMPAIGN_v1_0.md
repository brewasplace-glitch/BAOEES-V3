# PROJECT PHOENIX 4.41 — Phase 14 Repeatable Level-4 Campaign v1.0

Phase 14 advances the proven Phase-13 Level-4 batch into one bounded campaign
of exactly two sequential batches. Each batch contains exactly three committed
LOW-risk non-executable documentation-evidence tasks and is independently
backup-first, isolated, test-gated, fast-forward promoted and normally pushed.

Campaign progress is stored outside the repository in an HMAC-bound SQLite
checkpoint. A process restart may resume only when the checkpoint, current
local and remote baseline, completed output hashes, policy digest and backlog
digest agree exactly. Ambiguous post-push state fails closed for manual
reconciliation.

Each batch may perform at most one deterministic trailing-whitespace repair.
Security, policy, dependency, isolation, regression and remote failures are
never repairable. A later batch failure preserves a previously proven batch;
cross-batch destructive rollback and partial current-batch promotion are
forbidden.

This is bounded Level 4, not Level 5: no daemon, continuous monitoring,
automatic dependency installation, policy change, registry change, source
change or engine activation is permitted.
