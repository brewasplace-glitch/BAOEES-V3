# PHOENIX AUTO SYNC — Professional Country-Aware End-to-End A/B Routing v1.0

Classification: EXTEND_ROUTING_ONLY.

Project Phoenix now exposes a project-level output target in the official start
screen.

A = `A-PROFESSIONAL`:
professional project output from design through structural report,
specification, specification drawings, quantities, country-aware cost estimate,
QA/QC, exports and final package. A does not claim formal construction release.

B starts as `B-PENDING` on the same project. Existing professional review and
release gates must close before `B-RELEASED` may be represented.

Relevant change after release:
`B-RELEASED -> B-REVIEW-REQUIRED`.

Default = A.

Country-aware costing is mandatory for the professional end-to-end workflow.
Country comes from explicit/authoritative project context. Missing local cost
evidence remains explicit; synthetic test data is not professional evidence.

No replacement architecture, structural, cost, document, CAD or release engine
was introduced.
