# Phoenix Cost Estimate Desired-Output Evidence Resolver Repair v1.0

## Proven root cause

The Level-A cost-planning adapter correctly emits `cost_estimate.json` and includes it in
`adapter_result.outputs`, but `desired_output_evidence.py` only recognized
`local_cost_calculation.json` for the `cost_estimate` desired output.

This caused `DESIRED_OUTPUT_ARTIFACT_REQUIRED` even though a concrete estimate artifact
was present.

## Repair

The resolver continues to support the legacy `local_cost_calculation.json` artifact and
also recognizes Phoenix Level-A `cost_estimate.json` when:
- `artifact_type` is `COST_ESTIMATE`;
- schema is the Phoenix Level-A cost-estimate schema;
- `pricing_rules.price_fabricated` is explicitly false;
- automatic professional approval remains false;
- production release remains locked.

No price is invented and the existing desired-output false-pass guard remains active.
