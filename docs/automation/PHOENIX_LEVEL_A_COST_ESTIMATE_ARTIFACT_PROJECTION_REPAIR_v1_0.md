# Phoenix Level-A Cost Estimate Artifact Projection Repair v1.0

## Proven blocker

`DESIRED_OUTPUT_ARTIFACT_REQUIRED` for `cost_estimate`.

The Cost & Planning Session Adapter passed, but emitted only planning/input/market-context
registers. The runtime contract explicitly states that unresolved current market price
evidence does not block estimate/planning generation, yet no concrete `cost_estimate`
artifact was emitted.

## Repair

The existing cost stack remains authoritative. Phoenix now emits
`cost_estimate.json` as a Level-A estimate artifact.

When current market evidence is unresolved:
- prices are not fabricated;
- numeric totals remain null;
- unresolved evidence and source registers are recorded;
- completion requirements are explicit;
- the artifact is professional-review-required;
- production and FOR CONSTRUCTION release remain locked.

This is an artifact-projection repair, not a new cost engine.
