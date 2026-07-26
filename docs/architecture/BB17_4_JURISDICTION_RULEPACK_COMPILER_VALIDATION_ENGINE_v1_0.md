# BB17.4 — Jurisdiction Rulepack Compiler & Validation Engine v1.0.0

BB17.4 converts verified BB17.3 source catalogs, approved rule mappings and
validated executable rule definitions into BB17-compatible code profiles.

Compilation is blocked when jurisdictions differ, required sources are not
verified, mappings are not approved, definitions are missing, or review status
is incomplete. Compiled profiles remain `pending-release-review` and cannot
claim regulatory compliance until a later jurisdiction-specific release gate
approves them.

The six current foundations — NL-EU, SR, BES, AW, CW and SX — are expected to
remain blocked because their legal rule content is still in foundation status.
This is a successful safety result, not an installation failure.
