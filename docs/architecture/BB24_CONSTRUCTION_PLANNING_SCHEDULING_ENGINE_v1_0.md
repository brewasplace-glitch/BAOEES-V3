# BB24 - Construction Planning & Scheduling Engine v1.0.0

## Position

BB20 Quantity Take-Off -> BB21 Cost Estimation -> BB22 BIM Coordination ->
BB23 Construction Documentation -> BB24 Construction Planning & Scheduling.

## Purpose

BB24 turns explicit work packages or BB20 quantities and BB21 costs into a
traceable construction programme.

## Scheduling foundation

- WBS-coded activities and milestones;
- finish-to-start dependencies with non-negative lag;
- deterministic topological sorting;
- critical-path forward and backward passes;
- early and late dates;
- total float and critical activity classification;
- Monday-Friday workday calendar with project holidays;
- links to model objects and BB20 quantity IDs.

## Automatic derivation

When explicit activities are absent, BB24 groups BB20 records by work section,
estimates duration with transparent productivity assumptions, allocates BB21
costs by quantity ID, assigns default crews, sequences the work sections and
adds a completion milestone.

## Resources and cashflow

BB24 calculates:

- total resource-days per resource type;
- peak concurrent demand;
- direct cost per activity;
- monthly cost phasing;
- cumulative cashflow.

## Scenarios

The default comparison contains:

- Baseline: duration factor 1.00 and cost factor 1.00;
- Accelerated: duration factor 0.85 and cost factor 1.08;
- Delayed: duration factor 1.20 and cost factor 1.03.

The factors are configuration assumptions and do not represent market quotes.

## Exports

- JSON planning report;
- CSV schedule, resource and cashflow registers;
- styled XLSX workbook with Summary, Schedule, Resources and Cashflow sheets;
- HTML Gantt report;
- SVG Gantt drawing;
- SHA-256 checksum register;
- complete planning dossier ZIP.

## Safety boundary

BB24 is a non-certifying planning foundation. Productivity, sequencing,
resources, calendars and costs require project-specific review before use for
contractual planning, procurement or site control.

## Quality gates

1. Python compilation.
2. Nineteen unit tests.
3. BB24 self-test.
4. JSON, CSV, XLSX, HTML, SVG and dossier ZIP validation.
5. Git whitespace validation.
6. Exact payload staging.
7. Automatic commit and push after all gates pass.
8. Transactional rollback before push and no history rewrite after push.
