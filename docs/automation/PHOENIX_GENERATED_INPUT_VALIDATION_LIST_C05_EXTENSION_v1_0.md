# Project Phoenix — Generated Input Validation List C05 Extension v1.0

## Classification

`EXTEND` — exact-contract reconciliation proved that C01-C04 and C06-C12 already
exist. Only C05, one unified list of Phoenix-generated inputs for human validation,
was missing/partial.

## Scope

This extension adds only the deterministic validation-list bridge:

generated Phoenix candidate inputs
→ C05 validation list
→ existing reviewer-friendly DOCX generation
→ existing returned-DOCX intake
→ existing explicit review merge
→ existing canonical JSON / provenance / SHA-256 / audit trail
→ existing downstream package validators.

It does **not** replace AAIE, the validation engine, document/DOCX engines,
professional dossier control, Package E, or C/D/E evidence intake.

## Validation classes

- `AUTO_DERIVED`
- `SOURCE_BACKED_CANDIDATE`
- `ASSUMED_CANDIDATE`
- `HUMAN_REQUIRED`
- `PROFESSIONAL_REVIEW_REQUIRED`

Every item receives a deterministic `PHX-VAL-*` field ID, original Phoenix value,
source, confidence, rationale, affected outputs, and an empty human review block.

## Open-source-first

Two suitable maintained open-source validation candidates were reviewed:

1. **Pydantic** — MIT; preferred optional typed/schema validator.
2. **python-jsonschema** — MIT; fallback optional JSON Schema validator.

No new mandatory dependency is added. C05 is list construction, while the existing
Phoenix stack already owns input generation, DOCX production/intake, review merge,
canonical JSON, audit and release safety.

## Safety

The list is concept input only. It never marks a reviewer action automatically,
never fabricates professional review or approval, and keeps production release
`LOCKED`.
