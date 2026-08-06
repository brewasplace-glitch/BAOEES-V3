# Project Phoenix Structural Material Design-Basis Gate Fix v1.0 — FIXED R5

## Purpose
Correct the separation between material availability/certification and the structural design basis.

## Rules
- In `UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED`, missing certification and missing/unknown availability do not trigger the legacy structural material availability gate.
- Unknown/unavailable supply is a procurement/release issue, not a design-engineering availability blocker.
- A missing required material/strength class is recorded separately as `STRUCTURAL_DESIGN_MATERIAL_BASIS_REQUIRED`.
- Supplier/product descriptions, availability evidence, candidate lists and commercial capability ranges may never define the required structural design class.
- A required design class may only be obtained from explicit design/specification/handoff/profile fields.
- No material values are fabricated. Downstream solver stages may still require a real structural design basis before numerical analysis.
- Production / for-construction release remains LOCKED where design-basis, certification or availability verification remains unresolved.
