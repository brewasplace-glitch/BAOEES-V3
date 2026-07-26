# BB25 - Procurement & Tendering Engine v1.0.0

## Position

BB20 Quantity Take-Off -> BB21 Cost Estimation -> BB22 BIM Coordination ->
BB23 Construction Documentation -> BB24 Construction Planning & Scheduling ->
BB25 Procurement & Tendering.

## Purpose

BB25 converts quantities, benchmark costs and programme dates into controlled
procurement packages and transparent tender comparisons.

## Procurement packages

The engine groups BB20 quantity records by work section and creates:

- deterministic package and tender-line IDs;
- scope descriptions;
- benchmark budgets from BB21;
- planned procurement periods from BB24;
- model-object and quantity traceability;
- minimum qualification requirements.

## Bid controls and normalization

BB25 validates supplier and bid identities, package references, bid currencies,
duplicate/missing/extra lines, line prices, validity, duration, exclusions and
commercial qualifications. Automatic currency conversion is disabled.

For every bid BB25 calculates the offered total, benchmark allowances for
omitted lines, evaluated total, completeness, price and delivery scores,
responsive status and deviation count.

## Award scenarios

BB25 provides review recommendations, never automatic contract awards:

1. Lowest evaluated cost: 80% price, 15% completeness, 5% delivery.
2. Balanced award: 55% price, 30% completeness, 15% delivery.
3. Schedule priority: 35% price, 20% completeness, 45% delivery.

## Exports

- JSON procurement report;
- package, tender-line, supplier, bid and recommendation CSV registers;
- styled XLSX procurement workbook;
- DOCX and PDF request for tender;
- SHA-256 checksum register;
- complete tender dossier ZIP.

## Safety boundary

BB25 is non-certifying and does not issue contracts, approve suppliers, convert
currencies or replace technical, legal and commercial review.
