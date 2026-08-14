# PROJECT PHOENIX — PAT-001 Identity Closure + Structural Preparation State Masterpack v1.3

Required baseline: `5b0cc499d39b3f07deceb75e4f6fc9812cc06ab9`

## Project-owner identity decision

Project ID: `PHOENIX-PAT-001`

Project name:

`Anijsstraat`

Structural scope:

`Constructief ontwerp en analyse van de volledige draagconstructie, inclusief fundering, kolommen, balken, vloeren/daken, stabiliteit en belastingafdracht.`

This is stored as an explicit project-owner strategic decision. It is not inferred from generic JSON names, file names, room names, load-case names or other project artifacts.

## Purpose

The v1.2 PAT-001 preparation state already established:

- complete structural provenance;
- valid Canonical Structural Model v1.1;
- confirmed analysis scope `LIN`;
- qualified existing PAT-001 CalculiX project adapter;
- no live solver execution during preparation.

The remaining preparation gaps were:

- `PAT001-GAP-IDENTITY`
- `PAT001-GAP-SCIA-MODEL`

v1.3 closes only the identity gap.

## Identity evidence

Durable declaration:

`configs/projects/pat001_project_identity_declaration_v1_3.json`

It records:

- project id;
- project name;
- structural scope;
- decision source;
- decision date;
- project-owner authority.

The existing traceable location from the v1.2 contract is preserved. v1.3 refuses to invent a location if the source contract does not contain one.

## New runtime contract

The v1.2 source contract is never overwritten.

The runner creates:

`projects/runtime/PHOENIX-PAT-001/structural_identity_v1_3/pat001_structural_input_contract_v1_3.json`

and:

`pat001_structural_preparation_state_v1_3.json`

## Expected resulting state

If canonical, provenance, analysis scope and CalculiX adapter evidence remain valid, and no qualified PAT-001 SCIA seed has appeared, the exact state is:

`PAT001_STRUCTURAL_PREPARATION_COMPLETE_SCIA_PENDING`

with exactly:

`PAT001-GAP-SCIA-MODEL`

remaining.

This state is not:

- a structural design approval;
- a code-compliance claim;
- a professional review;
- a FOR-CONSTRUCTION release;
- a production release.

## SCIA

SCIA remains separately gated.

No ESA is generated or fabricated.
No reference/golden ESA is substituted for PAT-001.
No SCIA execution occurs in this masterpack.

## Safety

No live SCIA.
No live CalculiX.
No automatic professional approval.
No automatic code-compliance claim.
Production and FOR-CONSTRUCTION remain LOCKED.
