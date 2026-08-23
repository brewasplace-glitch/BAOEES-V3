# PROJECT PHOENIX — EXISTING CAPABILITY + REUSE GATE v1.0

## Mandatory rule

Before a Phoenix masterpack adds a capability, this gate must classify the clean repository as exactly one of:

- `REUSE`: required contracts are present and required tests pass;
- `REPAIR`: implementation exists but a required test fails;
- `EXTEND`: related/partial capability evidence exists but required contracts are incomplete;
- `BUILD`: no implementation or discovery evidence is present.

A new-build masterpack must require `BUILD`. `REUSE`, `REPAIR`, and `EXTEND` block duplicate construction.

## Fail-closed behaviour

The gate refuses to classify a dirty worktree. Uncommitted files are not allowed to influence a reuse/build decision.

Discovery-only evidence also blocks a blind `BUILD`: if keywords/history indicate that Phoenix may already contain the capability but required implementation contracts are not proven, the gate returns `EXTEND` so the capability must first be reconciled.

## Evidence

The gate inspects, without mutating the repository:

- Git branch, HEAD and clean status;
- required paths in both HEAD and the worktree;
- required symbols via `git grep`;
- discovery keywords via `git grep`;
- relevant Git history;
- required Python tests, executed with the active Python interpreter unless disabled.

## Capability specification

```json
{
  "capability_id": "PHX.STRUCTURAL.LEVELS_TO_STOREYS",
  "description": "Route-aware canonical levels to generic storeys bridge",
  "keywords": ["levels", "storeys", "structural session"],
  "required_paths": ["phoenix/structural/example_bridge.py"],
  "required_symbols": ["levels_to_storeys"],
  "required_test_paths": ["tests/automation/test_example_bridge.py"],
  "optional_paths": []
}
```

## New-build preflight

```powershell
powershell -ExecutionPolicy Bypass -File ".\runners\PROJECT_PHOENIX_EXISTING_CAPABILITY_REUSE_GATE_v1_0.ps1" `
  -Spec ".\path\to\capability_spec.json" `
  -RequireDecision BUILD
```

Important stdout markers:

```text
EXISTING_CAPABILITY_GATE=REUSE|REPAIR|EXTEND|BUILD
CAPABILITY_ID=<id>
BUILD_REQUIRED=YES|NO
```

## Open-source-first review

Primary reference: ripgrep, dual licensed MIT/Unlicense, for fast recursive source search.

Fallback/reference: Semgrep/Opengrep, LGPL-2.1-family open-source static-analysis engines, for deeper structural code analysis.

Phoenix v1.0 adds no new runtime dependency. Git and the Python standard library already provide the required evidence primitives; external analyzers remain optional.

## Governance

This is a software-governance gate only. It does not claim code compliance, professional approval, or construction readiness.

Release status: `CONCEPT ONLY / NOT FOR CONSTRUCTION`.
