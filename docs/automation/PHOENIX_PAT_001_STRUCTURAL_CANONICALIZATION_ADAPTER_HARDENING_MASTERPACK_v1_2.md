# PROJECT PHOENIX — PAT-001 Canonical Structural Model + CalculiX Adapter + Harvest Hardening v1.2

Required baseline: `c215de4fd3989428fe3b9e6d559187fc8305fab5`

## Why v1.2 is needed

The PAT-001 evidence harvest established that the older v1.1 bootstrap layer was too broad in two places:

1. generic JSON `name` fields were incorrectly treated as possible project names;
2. `calculation_type` / `analysis_type` values from templates and load cases could pollute the global analysis-scope decision.

The real PAT-001 v8.3 structural model also contains frame and shell elements. A lossy conversion to the earlier member-centric Canonical Structural Model is prohibited.

## Canonical Structural Model v1.1

This pack introduces:

`phoenix.canonical-structural-model/1.1`

It explicitly contains:

- nodes;
- materials;
- sections;
- members;
- shells;
- supports;
- load cases;
- load actions;
- load combinations;
- metadata and source evidence.

The canonicalizer reads the existing PAT-001 v8.3 project input and performs only structural mapping. It does not invent geometry, material properties, section sizes, design classes, loads, combinations, units or boundary conditions.

All candidate-only and review-required source records remain traceable in the canonical model.

## Shell preservation

Shells are a hard contract.

If the source v8.3 model does not expose a shell list, canonicalization fails rather than silently treating the project as a frame-only structure.

## Analysis scope hardening

Only:

`v8_3/input.json -> solver_basis.analysis_type`

is used as the project analysis-scope source.

Accepted mapping in v1.2:

- `LINEAR_STATIC` -> `LIN`
- `LIN` -> `LIN`

Load-case `analysis_type = STATIC` is not used as the global solver scope.

`*_REQUIRED.json` and template files are never treated as authoritative project decisions.

## Project identity hardening

Generic JSON `name` is never accepted.

Only explicit project-manifest fields are eligible:

- `project_name`
- `project_title`
- `structural_scope`

If they are absent, the identity gap remains open.

## Existing CalculiX adapter registration

Phoenix already contains a project-capable v8.3 CalculiX route.

v1.2 does not create a competing adapter. It registers:

`PAT001-LEGACY-V8_3-CALCULIX-PROJECT-ADAPTER-v1`

only when all of the following exist:

- PAT-001 v8.3 input with exact project id;
- `calculix` declared in `solver_adapters`;
- the legacy v8.3 solver runner;
- the v8.3 solver-package manifest;
- an existing PAT-001 CalculiX project deck under v8.4 evidence.

All evidence is SHA-256 hashed.

Registration starts no solver.

## SCIA

This pack does not close the SCIA project-model gap.

A PAT-001 ESA remains acceptable only with genuine PAT-001 provenance and hash qualification. Reference/golden ESA files are not substituted.

## Expected post-run result

On the currently observed PAT-001 workspace, the expected direction is:

- Canonical gap: closable by v8.3 conversion;
- CalculiX adapter gap: closable by registration of existing project evidence;
- analysis-scope gap: closable only if the actual v8.3 solver basis contains a supported explicit value;
- identity gap: remains open unless explicit project_name/project_title + structural_scope exist;
- SCIA gap: remains open until a real PAT-001 SCIA project/seed exists.

## Safety

No live CalculiX or SCIA during installation or post-install preparation.
No automatic professional approval.
No automatic code-compliance claim.
Production and FOR-CONSTRUCTION remain LOCKED.
