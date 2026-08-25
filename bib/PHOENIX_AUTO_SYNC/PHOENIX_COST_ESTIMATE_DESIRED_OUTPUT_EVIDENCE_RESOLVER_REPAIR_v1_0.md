# PHOENIX AUTO SYNC — Cost Estimate Desired-Output Evidence Resolver Repair v1.0

Root cause: the cost adapter emitted a valid Level-A `cost_estimate.json`, but the central
desired-output evidence resolver accepted only the legacy `local_cost_calculation.json`.

Repair: recognize both contracts. A Level-A estimate is accepted only when it is a Phoenix
COST_ESTIMATE artifact, price_fabricated=false, automatic professional approval is false,
and production release is LOCKED.

This closes only the artifact-recognition mismatch. It does not resolve missing current
market price evidence and does not create a professional/release claim.
