# PHOENIX 4.41 — Anijstraat #616 Structural Input + Gap Analysis

## Purpose

Real-project intake gate before structural derivation and calculation.

## User-authority decisions

- No geotechnical report is available. Phoenix may create a conservative preliminary soil/groundwater model and must record assumptions and sensitivity cases.
- Timber species and strength class are unknown. Phoenix may select a documented preliminary strength class and must verify the roof members.
- Elevated durotank volume is 2.0 m³.
- Existing structural sizes on the architectural set are **unverified proposals**, not accepted calculations.

## Mandatory governance

- `PRELIMINARY_NOT_FOR_CONSTRUCTION = TRUE`
- `PROFESSIONAL_STRUCTURAL_REVIEW_REQUIRED = TRUE`
- `FOR_CONSTRUCTION_RELEASE = LOCKED`
- Drawing conflicts must be explicit. No silent reconciliation.
- Site-specific geotechnical investigation remains a release blocker.

## Open-source-first intake

Primary: `pdfplumber` (MIT) for machine-generated PDF text/layout extraction.
Fallback: `pypdf` for pure-Python text/metadata extraction.

Dependencies are not vendored. The installer can place them in the user's local Phoenix runtime-dependency directory when not already available.

## Next stage on PASS

`PHOENIX 4.41 REAL-PROJECT STRUCTURAL DERIVATION + LOAD MODEL — ANIJSTRAAT #616`
