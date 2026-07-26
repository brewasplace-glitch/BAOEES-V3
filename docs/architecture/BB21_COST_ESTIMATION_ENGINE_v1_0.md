# BB21 — Cost Estimation Engine v1.0.0

## Position

BB20 Quantity Take-Off → BB21 Cost Estimation.

## Purpose

BB21 prices traceable BB20 quantity records with a controlled, versioned
rate book. It separates material, labor, equipment, subcontract and other
components and generates multiple project scenarios without changing the
original quantities or rate source.

## Cost controls

Every rate book records currency, price date, jurisdiction, location profile,
validation status and source reference. BB21 v1.0 never performs currency
conversion and rejects scenarios using a different currency.

Each scenario can apply quantity, location, escalation and component factors.
Project additions are calculated in this sequence:

1. direct cost;
2. overhead;
3. risk;
4. contingency;
5. profit;
6. tax.

## Rate matching

Rates select BB20 records by unit and one or more controlled fields:
quantity type, element category, work section, material and source model.
The most specific unique match is used. Missing or equally specific competing
rates are reported and are not priced.

## Output

- scenario summaries;
- cost lines linked to BB20 quantity IDs, model objects and drawing references;
- totals by work section, level and cost code;
- JSON, UTF-8 CSV and dependency-free XLSX exports;
- deterministic rate-book, quantity-report and estimate fingerprints.

## Safety boundary

The bundled rate book contains synthetic values for automated tests only. It
is not market data and must not be used for a real estimate. Project estimates
require a separately sourced, dated and validated rate book for the selected
country, region, currency and project.

BB21 v1.0 is concept-stage and non-certifying. It does not replace quotations,
procurement validation, tax advice or professional quantity-surveyor review.
