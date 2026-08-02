# Phoenix Generic Session Adapter Masterpack v1.0

## Purpose
Connect the Session-Driven Orchestrator to seven generic project capability adapters:

1. Architectural Session Adapter
2. Digital Twin Session Adapter
3. Structural v8.0–v8.12 Session Adapter
4. Permit / BOPA / AERIUS Session Adapter
5. Cost & Planning Session Adapter
6. Reporting Session Adapter
7. QA/QC / Review / Release Session Adapter

All seven consume the same:
- current `session_file`
- project workspace
- project manifest
- desired-output selection
- upload-batch reference
- project ID

## Safety contract
The masterpack removes `MISSING_GENERIC_CAPABILITY` as an integration defect,
but it does not fabricate missing engineering input.

An adapter may return controlled `BLOCKED` (exit code 10) when, for example:
- no dimensioned/structured architecture geometry is available;
- no project-specific structural profile exists;
- no project location/jurisdiction is known;
- no ratebook/currency has been selected;
- an upstream discipline has not passed.

This is an engineering input blocker, not a missing adapter.

## Structural adapter
The structural adapter registers and verifies the generic v8.0–v8.12 chain.
It can safely execute v8.0 when the required architectural model, detailed
elements and project structural profile exist. It does not invent cross-version
input transformations; later stages remain release-locked until their contracts
are explicitly satisfied.

## Reporting and closure
Reporting always produces an autonomous status report from the current adapter
state. Closure always produces a QA/QC release gate and keeps production release
locked unless the required upstream work and human review are complete.

## Result index
The orchestrator now writes `results/result_index.json` v1.1 with:
- capability state per adapter
- desired-output state
- produced paths
- blocked outputs
- passed outputs
- production release state

## FIXED R1
The first install attempt passed all 61 functional/regression tests and then correctly stopped at `git diff --check` because `phoenix/autonomy/session_orchestrator.py` had a new blank line at EOF. R1 removes that whitespace-only defect, normalizes trailing whitespace in the payload, and adds regression coverage. Runtime behavior is unchanged.
