# Project Phoenix Structured Product Evidence + Material Route + Landed Cost Gate v1.0

## Purpose

This package closes the gap proven by PHOENIX-PAT-001 where the Brave supplier discovery provider was active but Phoenix ended with `NO_STRUCTURED_GLOBAL_PRODUCT_EVIDENCE_ACQUIRED`.

## Production rules

1. Search-engine results are discovery evidence only. Snippets never qualify a structural product.
2. Phoenix fetches the source product page and, when exposed by that page, technical documents such as a TDS, DoP, CE-related document, inspection certificate or mill certificate.
3. Engineering qualification is conservative and material-family specific. Missing evidence remains a blocker.
4. Structural ready-mix concrete is routed to local Suriname technical qualification. Ordinary ready-mix is not treated as a normal Europe-to-Paramaribo import commodity.
5. Masonry is local-first with international fallback only if local technical qualification cannot be completed.
6. Structural timber and reinforcement steel use local-first, then Netherlands, Belgium, EU27 and global fallback.
7. No order, payment or professional approval is performed automatically.
8. Production release remains LOCKED.
9. Landed cost cannot report PASSED merely because `selected_imports` is empty. If import is required and complete landed-cost evidence is absent, the gate is BLOCKED. If no import is required, the correct state is NOT_APPLICABLE.

## Evidence written per project

- `sources/import_acquisition/structured_product_evidence_acquisition_register.json`
- `sources/import_acquisition/global_import_evidence_acquisition_register.json`
- `sources/import_acquisition/search_audit/*.json`
- `sources/import_acquisition/fetched_evidence/*.json`
- technically qualified normalized product catalogs under `sources/material_supply/IMP_STRUCTURED_*.json`

The Brave credential itself is never persisted into repository or project evidence.

## FIXED R1 installation integration

FIXED R1 resolves the Phoenix session-adapter ambiguity explicitly: `run_architecture` is the
producer of the architecture material sourcing and landed-cost registers, while
`run_digital_twin` and `run_cost_planning` are downstream consumers. The landed-cost guard is
therefore attached only to `phoenix/autonomy/session_adapters.py::run_architecture`.
