# BB22 — BIM Coordination Engine v1.0.0

## Position

BB16 Building Model → BB18.1 Architectural Drawings → BB19 Structural Design
→ BB20 Quantity Take-Off → BB21 Cost Estimation → BB22 BIM Coordination.

## Purpose

BB22 creates one deterministic coordination layer across discipline models and
their downstream quantity and cost registers.

## Checks

- missing and duplicate stable object identifiers;
- conflicting project identifiers;
- semantic category differences for shared object IDs;
- level-assignment differences;
- shared-object bounding-box drift;
- selected hard clashes between openings, MEP, stairs and structural objects;
- BB20 quantities that reference unknown objects;
- measurable model objects without BB20 quantities;
- BB21 cost items that reference unknown quantities;
- BB20 quantities without BB21 cost items.

## Geometry

v1.0.0 uses axis-aligned bounding boxes and a configurable tolerance. This is a
fast, deterministic coordination foundation. Exact mesh and solid geometry
intersection remains a later IfcOpenShell/FreeCAD/Blender-enabled extension.

## Issues

Every issue receives:

- deterministic Phoenix issue ID;
- type, title, description, severity and status;
- discipline and responsible model context;
- source and target object IDs;
- level and issue location;
- machine-readable evidence.

An open `error` or `critical` issue blocks `coordination_passed`.

## Exports

- JSON coordination report;
- UTF-8 CSV issue register;
- dependency-free XLSX workbook;
- BCF-compatible foundation ZIP with one topic and viewpoint per issue.

The BCF export is a Phoenix foundation profile, not yet a formally certified
implementation of every optional BCF exchange feature.

## Safety boundary

BB22 is non-certifying. It assists model coordination but does not replace
professional design review, authoritative clash checks or discipline approval.

## Quality gates

1. Python compilation.
2. Twelve BB22 unit tests.
3. BB22 self-test.
4. JSON, CSV, XLSX and BCF-foundation export validation.
5. Git whitespace validation.
6. Exact payload staging.
7. Automatic commit and push only after every gate passes.
8. Transactional rollback before push and no history rewrite after push.
