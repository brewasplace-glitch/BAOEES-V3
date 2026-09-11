# PHOENIX 4.41 — Anijstraat #616 Structural Design Consolidation + Drawings

Expected source SHA256: `1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0`.

This stage consumes a verified solver result plus the derived load model and produces a controlled preliminary structural drawing set.

## Consolidated preliminary choices

- 150×200 mm RC ring beam is preferred over the conflicting 100×150 / 100×200 source details for coordination robustness. Preliminary detailing: 2Ø12 top + 2Ø12 bottom, Ø8-150 ties.
- 200×200 mm RC column with 4Ø12 and Ø8-150 ties is retained provisionally because the modeled axial utilization is low; combined N-M, second-order effects and lateral-system behavior remain HOLD.
- Source 800×200 strip footing and 1000×1000×200 pad geometry are retained only as gravity-bearing preliminary geometry; reinforcement, settlement, punching and final geotechnical design remain HOLD.
- Source 2×3 purlins may only be retained where actual unsupported span is proven ≤1.55 m.
- Source 2×4 rafters may only be retained where actual unsupported span is proven ≤2.00 m.
- For an unproven span up to 3.40 m, Phoenix uses 50×150 mm C18-proxy as the conservative preliminary roof coordination size.
- Elevated 2.0 m³ tank uses 23.54 kN preliminary gravity envelope; support frame, wind, overturning and anchorage remain HOLD.

## Drawing set

- S-01 Design basis + element schedule (SVG)
- S-02 Structural grid / foundation concept (SVG + DXF)
- S-03 Roof framing span rules (SVG + DXF)
- S-04 Typical preliminary structural details (SVG + DXF)
- S-05 Release hold / traceability matrix (SVG)

The source foundation/roof/section/detail sheets are also rendered to PNG when the existing Phoenix PDF renderer is available.

## Important

Phoenix does **not** invent interior loadbearing wall or column vectors that have not yet been structurally mapped from the architectural plan.

`PRELIMINARY_NOT_FOR_CONSTRUCTION = TRUE`
`FOR_CONSTRUCTION_RELEASE = LOCKED`
