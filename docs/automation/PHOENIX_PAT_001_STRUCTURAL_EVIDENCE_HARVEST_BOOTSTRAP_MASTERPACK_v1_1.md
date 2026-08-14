# PROJECT PHOENIX — PAT-001 Structural Evidence Harvest + Contract Bootstrap v1.1

Required baseline: `21e41a113eb79bacfe193609c5309f7667b8f114`

## Current reason for this layer

The first PAT-001 preparation assessment correctly returned six gaps:

- analysis scope;
- CalculiX adapter;
- canonical structural model;
- project identity;
- structural provenance;
- SCIA project model.

This v1.1 layer tries to close only those gaps that are already supported by traceable PAT-001 data in the repository.

## Conservative harvesting rules

Phoenix scans:

- `projects/runtime/PHOENIX-PAT-001`
- `configs/projects`
- `configs/phoenix/structural`

Project identity is auto-filled only from JSON that explicitly identifies `PHOENIX-PAT-001`.

A Canonical Structural Model is selected only if:

- schema is exactly `phoenix.canonical-structural-model/1.0`;
- it is PAT-001 scoped or explicitly identifies PAT-001;
- the installed canonical validator passes it;
- exactly one valid candidate exists.

Conflicting values are never guessed.

## Provenance

A provenance category becomes `TRACEABLE` only when a PAT-001 source actually contains matching structural content.
The bootstrap audit stores file path, SHA-256 and matching field paths.

## SCIA

A candidate seed is accepted only when a PAT-001 JSON source explicitly provides:

- an ESA seed path;
- `project_id = PHOENIX-PAT-001`;
- an exact 64-character SHA-256;
- and that SHA-256 matches the file.

Otherwise the SCIA gap remains open.

## CalculiX

A project adapter is accepted only from an explicit PAT-001 declaration.
Golden Reference deck generation does not count as a PAT-001 arbitrary-project adapter.

## Output

The existing v1.0 input contract is never overwritten.

A new runtime contract is written:

`pat001_structural_input_contract_v1_1.json`

plus an audit manifest and a fresh PAT-001 assessment.

## Safety

No project data is invented.
No live SCIA or CalculiX.
No automatic professional approval.
No automatic code-compliance claim.
Production and FOR-CONSTRUCTION remain LOCKED.
