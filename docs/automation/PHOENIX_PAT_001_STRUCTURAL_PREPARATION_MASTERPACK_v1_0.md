# PROJECT PHOENIX — PAT-001 Structural Preparation Masterpack v1.0

Required baseline: `443d2553c39bf1bede9b8aecd54c45c1faf396cb`

## Objective

Prepare PHOENIX-PAT-001 for the real structural solver chain without fabricating missing project engineering data.

The preparation engine separates:

1. project identity and structural scope;
2. Canonical Structural Model;
3. source provenance for geometry, materials, sections, supports, loads and combinations;
4. explicit project analysis scope;
5. qualified SCIA project model/seed evidence;
6. PAT-001 CalculiX project adapter;
7. analytical spot-check planning;
8. solver execution;
9. technical verification;
10. professional review.

Only items 1–7 belong to preparation.

## Hard rule for historical ESA files

An `.ESA` discovered in runtime/history/reference folders is only a candidate.

It becomes a qualified PAT-001 SCIA seed only when:

- the exact file exists;
- provenance explicitly names `PHOENIX-PAT-001`;
- provenance supplies its exact SHA-256;
- the declared SHA-256 matches the file.

Reference-model ESA files can never become PAT-001 project evidence merely because they are technically compatible.

## Canonical model

PAT-001 must use the installed Phoenix Canonical Structural Model validator.
No arbitrary project geometry is inferred from a Golden Reference benchmark.

## SCIA

Preparation may point to an existing qualified seed + XML/DEF package, but:
- no proprietary binary ESA is synthesized;
- no live SCIA calculation is started;
- SCIA license readiness remains a separate gate.

## CalculiX

Golden Reference success proves the CalculiX pathway, not the PAT-001 project model.
PAT-001 still requires a project-specific adapter for its arbitrary canonical model.

## Expected current state

Unless project-specific PAT-001 structural input has already been populated, the first real assessment is expected to stop safely at one of:

- `PAT001_STRUCTURAL_INPUT_CONTRACT_REQUIRED`
- `PAT001_CANONICAL_MODEL_REQUIRED`
- `PAT001_STRUCTURAL_PROVENANCE_REQUIRED`
- `PAT001_ANALYSIS_SCOPE_REQUIRED`
- `PAT001_SCIA_PROJECT_MODEL_REQUIRED`
- `PAT001_CALCULIX_PROJECT_ADAPTER_REQUIRED`

That is a preparation result, not a failure of Phoenix.

## Safety

No live SCIA or CalculiX during installation or assessment.
No automatic professional approval.
No automatic code-compliance claim.
Production and FOR-CONSTRUCTION remain LOCKED.
