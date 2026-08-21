# PROJECT PHOENIX — Moskee Structural Capability Activation Repair v1.0

## Bound baseline
`project-phoenix` @ `af28815d61966e6badca33b057b269ad9c27ec16`

## Proven root cause
The exact output-capability diagnostic proved:

- `structural_engineering` exists and is adapter-ready;
- it depends on `architecture` and `digital_twin`;
- the structural v8.0–v8.12 runner exists;
- CalculiX primary and fallback runtimes are installed;
- the Moskee binding currently requests none of the five output tokens that map to
  `structural_engineering`;
- therefore `structural_engineering` is absent from the derived capability closure.

The exact supported structural output tokens are:

- `calculations`
- `structural_drawings`
- `foundation_drawings`
- `structural_analysis`
- `foundation_design`

## Repair
This bounded repair changes only the Moskee E2E binding and activates all five existing
structural desired-output tokens. This intentionally exercises the complete existing
structural capability rather than creating a new engine or bypassing orchestration.

The orchestrator remains unchanged. The existing transitive dependency logic is expected
to select:

`architecture -> digital_twin -> structural_engineering`

and the existing structural adapter then drives the v8.0–v8.12 chain, including the
project-scoped v8.3 solver package.

## Validation
Before commit:
- binding schema/readability;
- structural token mapping tests;
- exact capability-closure smoke;
- existing nonresidential router regression;
- existing structural session-chain tests when present;
- git diff check;
- secret scan.

After gates:
- BIB precommit hook;
- commit/push;
- post-commit BIB validation;
- clean/synchronized repository;
- full Moskee real-project E2E rerun.

Success target:
- architectural E2E remains PASS;
- a project-scoped `.inp` exists;
- real CalculiX execution runs;
- no production/FOR-CONSTRUCTION unlock is introduced.
