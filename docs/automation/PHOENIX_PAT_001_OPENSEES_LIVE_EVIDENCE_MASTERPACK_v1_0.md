# PROJECT PHOENIX — PAT-001 OpenSees Live Execution + Raw Evidence + Results Normalization + Adapter Qualification v1.0

Required baseline: `e71839f6037d8cad40dec81985e1747bc0e19c0a`

Project: `PHOENIX-PAT-001` / `Anijsstraat`

This masterpack promotes the existing v8.3 OpenSees solver-package route into a governed live project route.

## Important compatibility hardening

The existing v8.3 OpenSees generator assigns member and shell element tags independently. For a mixed frame/shell project those tag ranges can overlap. The new runtime never overwrites the v8.3 source deck. It creates a hash-traceable execution copy, preserves member tags, and if needed moves shell tags deterministically after the maximum member tag.

The existing v8.3 deck already emits Phoenix node displacement/reaction lines. The execution copy inserts `reactions` immediately before node reaction capture.

## Live execution governance

Live project execution requires the explicit `-AllowLiveExecution` switch. Without it Phoenix only discovers OpenSees, prepares hardened execution copies, and writes readiness evidence.

## Raw evidence

Every live base case stores source deck, execution deck, executable SHA-256, command, return code, stdout, stderr, normalized results and a case manifest.

## Normalization

Phoenix normalizes all node displacement and reaction vectors. Element force/stress responses are captured best-effort via `eleResponse`; unavailable channels remain empty and are never fabricated. Global applied-force sum, reaction sum and residual are stored without inventing an engineering acceptance tolerance.

## Qualification

The adapter is qualified only when every base case exits zero, emits `PHOENIX_ANALYSIS_OK`, emits `PHOENIX_EVIDENCE_CAPTURE_OK`, and normalizes all expected node displacement/reaction vectors.

Qualified technical state: `CALCULATED_UNVERIFIED`.

No professional approval, code-compliance or independent-verification claim is created. `PAT001-GAP-SCIA-MODEL` is unchanged. Production and FOR-CONSTRUCTION remain LOCKED.
