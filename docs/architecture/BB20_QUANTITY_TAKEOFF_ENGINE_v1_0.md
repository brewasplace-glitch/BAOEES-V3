# BB20 — Quantity Take-Off Engine v1.0.0

## Position

BB16 Building Model → BB18.1 Architectural Drawings → BB19 Structural Design
→ BB20 Quantity Take-Off.

## Purpose

BB20 generates traceable concept quantities from canonical building and
structural model objects. Every record retains the source model, object ID,
level, material, calculation formula, input dimensions, assumptions and drawing
references.

## Initial measurement rules

- walls: count, length, gross area, volume and optional mass;
- slabs and roofs: count, area, volume and optional mass;
- beams and foundations: count, length, volume and optional mass;
- columns: count, height, volume and optional mass;
- doors and windows: count and area;
- stairs: count and estimated plan area;
- generic, site and MEP objects: count;
- declared model quantities: accepted with explicit declared provenance.

When a structural object has the same ID as a structural-category object in the
building model, the structural model takes precedence to prevent double
counting.

## Output

- deterministic JSON report;
- UTF-8 CSV measurement register;
- dependency-free XLSX workbook with Quantities and Summary worksheets;
- totals by unit, work section, material and building level;
- issues for missing, invalid or conflicting model data.

## Safety boundary

v1.0.0 quantities are concept-stage and non-certifying. Orthogonal elements are
measured as simplified prisms or plates. Openings are not automatically deducted
from gross wall areas unless a later net-measurement rule or declared quantity
provides that information.

BB20 does not assign prices. Cost classification and rate application belong to
BB21 Cost Estimation Engine.

## Quality gates

1. Python compilation.
2. Ten BB20 unit tests.
3. BB20 self-test.
4. JSON, CSV and XLSX export validation.
5. Git whitespace validation.
6. Exact payload staging.
7. Automatic commit and push only after all checks pass.
8. Transactional rollback at the first failure.
