# Project Phoenix v8.4 â€” CalculiX Instrumented Set Wrap FIXED R6 Masterpack v1.0

## Runtime evidence

PHOENIX-PAT-001 after commit `378aee6` proved that the v8.3 NALL fix worked:
the v8.3 source deck contained no CalculiX data line above 16 entries.

The next real solver blocker was introduced by v8.4 instrumentation:

- keyword: `*NSET, NSET=PHX_SUPPORT_NODES`
- support IDs: 34
- emitted on one line
- CalculiX 2.22 exit code: 201
- parser error: more than 16 entries in a line

The source was `_instrument_deck()` in
`phoenix/autonomy/autonomous_calculix_results_v8_4.py`.

## R6 correction

R6:

1. adds `_calculix_set_data_lines(...)`;
2. writes `PHX_SUPPORT_NODES` in deterministic chunks of at most 16 IDs;
3. adds `_validate_calculix_set_card_width(...)`;
4. validates every `*NSET` and `*ELSET` data row in the fully instrumented deck;
5. blocks before solver execution if a generated set row exceeds the limit;
6. adds regression coverage for the actual 34-support-node pattern.

## Scope

R6 changes only:

- the v8.4 CalculiX instrumentation/result module;
- one dedicated R6 regression test;
- this evidence document.

The already-corrected v8.3 deck writer is not changed.

## Safety

R6 does not enable automatic code compliance, professional approval,
for-construction release, or production release.