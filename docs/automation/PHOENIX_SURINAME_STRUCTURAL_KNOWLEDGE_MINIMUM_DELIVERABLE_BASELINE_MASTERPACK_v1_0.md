# Phoenix Suriname Structural Knowledge & Minimum Deliverable Baseline Masterpack v1.0

## Purpose

This masterpack converts three user-provided Suriname reference dossiers into structured Phoenix knowledge while preserving a strict separation between:

1. reusable delivery/template knowledge;
2. engineering-practice evidence that still requires project validation;
3. project-specific values that must never silently become global defaults.

## Reference evidence

- `01 CONSTRUCTIERAPPORT constructie Roger_260531_165317.pdf`
- `22029 - Architect - Funderingsberekening Woonhuis Virolastraat-KV-24aug22 + att.pdf`
- `plafond 3.5 m ow tekening Huis Wartes Anijstraat 616(1).pdf`

The original PDFs are not copied into this pack. Phoenix stores only a derived knowledge/evidence catalog and the minimum deliverable contract.

## Minimum drawing baseline

The reference drawing package contains 15 A3 sheets. Phoenix therefore records a 15-sheet reference delivery level covering:
floor plan, foundation, sewerage, four facades, roof plan, sections, details, septic tank when applicable, opening schedule, information/finishes, water, HVAC when applicable, electrical and site/location drawing.

## Structural report baseline

A completed Phoenix building project must explicitly address:
project/scope, code basis, materials, actions and combinations, structural model, UGT/BGT, applicable slabs/beams/columns, roof structure, foundation/geotechnics, reactions, connections where applicable, structural drawings and QA/review.

## Status contract

Every baseline item must end as exactly one of:

- `GENERATED_AND_VALIDATED`
- `NOT_APPLICABLE_WITH_REASON`
- `BLOCKED_WITH_EXPLICIT_REASON`

A missing output is never silently treated as not applicable.

## Suriname engineering policy

The user's approved interim engineering policy is recorded as a project/organization engineering policy: Dutch/Eurocode-style load-combination methodology may be used for Suriname, with snow action excluded unless project-specific evidence requires otherwise.

This is not labeled as verified Surinamese law. Current project evidence and professional engineering review remain required.

## Release safety

The session-adapter closure hook evaluates the baseline for autonomous Suriname building projects. If the baseline is incomplete and the existing closure runner would otherwise pass, the hook returns controlled BLOCKED code 10.

Even a content-complete baseline does not create professional approval. Production release remains locked until the existing professional review/release process is satisfied.
