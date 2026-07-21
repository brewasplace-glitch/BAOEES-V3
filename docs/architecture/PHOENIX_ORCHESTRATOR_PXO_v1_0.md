# Phoenix Orchestrator (PXO) v1.0

PXO is the central deterministic workflow coordinator between the selected
Phoenix Project Generator concept and the discipline engines.

It establishes the dependency graph for:

- GIS;
- geotechnical analysis;
- traffic and parking;
- foundation;
- structural engineering;
- steel and concrete specializations;
- fire safety;
- water, sewer, climate and electrical systems;
- sustainability;
- cost;
- permits;
- planning;
- BIM;
- Digital Twin;
- final dossier.

PXO only marks an engine as completed when it has been explicitly started and
returns at least one output and one evidence item. Missing engines remain
blocked or skipped and are never presented as completed work.

The workflow is deterministic, dependency-driven and auditable. Every state
transition updates the plan fingerprint and appends an audit entry.

PXO v1.0 is an orchestration contract. Future waves will add runtime adapters,
retry policy, persistent state storage, parallel execution groups and direct
handoff to Phoenix Autonomous Project Delivery.
