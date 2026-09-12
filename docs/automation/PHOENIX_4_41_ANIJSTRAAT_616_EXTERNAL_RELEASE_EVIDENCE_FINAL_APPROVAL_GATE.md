# PHOENIX 4.41 - Anijstraat #616 External Release Evidence Ingestion + Final Approval Gate

Expected clean baseline:

`b50e38d425430c870190c8616f9b1aafb82e1676`

Expected source SHA256:

`1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0`

## Purpose

This stage installs a reusable evidence-ingestion and approval-gate capability for the eight remaining structural release holds.

It creates a persistent user evidence inbox under Downloads with H01-H08 subfolders and submission templates. Future authoritative documents can be placed there and processed by rerunning the repository runner.

## Evidence policy

Phoenix validates:

- JSON Schema structure;
- evidence file existence;
- SHA256 integrity when supplied;
- optional Ed25519 detached signatures.

Phoenix does **not** infer from those checks that:

- a legal authority is competent;
- a geotechnical report is technically acceptable;
- a supplier statement establishes the required engineering properties;
- a person is professionally qualified;
- a structural design is approved for construction.

Those remain engineering/legal/professional acceptance steps.

## Expected first-run outcome

No new external evidence has yet been supplied, so the expected first-run result is:

`INGESTED_SUBMISSIONS = 0`

`OPEN_RELEASE_HOLDS = 8`

`FINAL_APPROVAL_GATE_STATE = HOLD_NO_EXTERNAL_RELEASE_EVIDENCE_INGESTED`

`FOR_CONSTRUCTION_RELEASE = LOCKED`

The capability itself may still PASS and be committed because it is the infrastructure needed to ingest later evidence safely.


## FIX R1 — dependency-aware test sequencing

The first Windows execution stopped in installer stage 3 because `engine.py --self-test` invoked JSON Schema validation before the isolated external-evidence runtime was installed.

FIX R1 changes the sequence:

1. installer: dependency-free `py_compile` + unit tests;
2. runner: install/reuse isolated external-evidence runtime;
3. explicit import probe for jsonschema, cryptography, docx, reportlab and pypdf;
4. runtime self-test;
5. evidence inbox bootstrap and real-project gate.

No evidence rule, hold state, structural result or release policy is changed.

## FIX R2 — Git whitespace / line-ending normalization

FIX R1 completed the real external-evidence gate successfully but stopped at the
commit preflight because the repository runner had malformed CRCRLF-style line
endings. Git therefore interpreted the carriage-return bytes as trailing
whitespace on every line.

FIX R2 rewrites the tracked PowerShell runner as UTF-8 without BOM and LF-only
line endings, strips trailing spaces/tabs, and adds an explicit runner
line-ending/whitespace gate before staging and commit.

No evidence result, hold state, structural result, approval policy, or release
decision is changed.
