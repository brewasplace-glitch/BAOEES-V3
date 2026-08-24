# Project Phoenix Professional Country-Aware Design-to-Construction + Cost A/B Routing v1.0

## Build classification

`EXTEND_ROUTING_ONLY`

The preceding capability reconciliation proved that the required Phoenix
capabilities already exist and are reusable. This integration therefore does
not create replacement architecture, structural, specification, cost,
document, CAD, QA/QC, or release engines.

## Start-screen contract

Every project now has an explicit output-level choice:

### A — Professionele projectoutput

Default.

Phoenix requests the existing professional end-to-end output set:
architectural design, 2D drawings, BIM/IFC/3D, structural analysis,
constructierapport, constructietekeningen, bestek, bestekstekeningen,
hoeveelheden, country-aware kostenraming, QA/QC, source evidence, office/CAD/XLSX
exports and final project package.

A is professional project output, but is not an automatic professional approval
or FOR CONSTRUCTION release.

### B — Formeel gecontroleerd / voor uitvoering

B is a target, not an automatic release.

Selecting B on the same project produces `B-PENDING`. Existing Phoenix
professional review, evidence and release gates decide whether the project can
eventually become `B-RELEASED`.

No new project is required when moving from A to B.

If a relevant project revision changes after B release, the state contract is:

`B-RELEASED -> B-REVIEW-REQUIRED`

Affected review/release gates must then be closed again.

## Country-aware costing

Professional A and B routing always set:

`country_aware_costing_required=true`

The country must come from explicit project data or an existing authoritative
project context. Phoenix must not infer the project country from UI locale.

Currency may be explicit or derived from the explicit project country under the
existing Phoenix jurisdiction/currency policy.

Current local price evidence is preferred. A synthetic test ratebook is not
professional cost evidence. Missing required local price evidence remains an
explicit blocker instead of being silently replaced with fabricated local
prices.

## Integration mechanism

The official start screen receives a small A/B routing extension. It does not
replace the existing start screen.

The extension:
- remembers A/B choice per selected project in the local start-screen session;
- automatically checks matching existing professional-output items;
- adds the A/B target and fail-closed release flags to normal project-start POST
  payloads;
- adds durable plain-text routing markers to the project brief so downstream
  Phoenix sessions can see the target even where unknown JSON fields are not
  persisted by a legacy adapter;
- never marks B as released by itself.

The Python state contract provides the same transition semantics for backend
consumers and later database integration.

## Safety

Automatic professional approval: disabled.

Automatic FOR CONSTRUCTION release: disabled.

B release: fail closed and dependent on existing professional/release evidence.
