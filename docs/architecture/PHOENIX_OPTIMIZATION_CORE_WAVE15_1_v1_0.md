# Phoenix Optimization Core — Wave 15.1 v1.0

## Purpose

Wave 15.1 introduces the deterministic optimization kernel for Project Phoenix.
It evaluates engineering variants produced by upstream structural, BIM and
drawing workflows.

## Capabilities

- hard-constraint filtering;
- minimize and maximize objectives;
- deterministic min-max normalization;
- Pareto dominance and Pareto-front extraction;
- weighted ranking;
- objective-weight sensitivity scenarios;
- canonical JSON and SHA-256 evidence;
- JSON-compatible PXO adapter;
- atomic result writing.

## Input contract

Each variant contains:

- a unique `variant_id`;
- numeric, finite `metrics`;
- optional descriptive `attributes`.

All configured objective metric names must exist in every variant. Missing hard
constraint metrics make that variant infeasible.

## Determinism

Variants are sorted by identifier before evaluation. Ranking ties are resolved
by `variant_id`. JSON evidence is generated from canonical, sorted-key JSON.

## Explicit limitations

Wave 15.1 does not:

- generate structural alternatives;
- perform finite-element analysis;
- dimension concrete, steel, timber or masonry;
- maintain price or environmental datasets;
- produce approval, permit or construction evidence.

Those concerns remain with upstream engines or later Wave 15 increments.

## Review status

All results are generated for engineering review. Final engineering judgement,
code compliance and approval remain the responsibility of qualified persons.
