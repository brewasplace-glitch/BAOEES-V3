# PHOENIX R6 — Release-Gate Binding

R6 canonical BIM/IFC geometry QA is bound into the existing BB36
`CommercialReleaseEngine.create_release()` contract.

Binding rules:
- reuse the existing Commercial Release Masterpack;
- R6 is an additional fail-closed technical prerequisite;
- missing R6 evidence blocks BB36 production release;
- failed or tampered R6 evidence blocks BB36 production release;
- valid R6 evidence must use schema
  `PHOENIX_R6_RUNTIME_CANONICAL_GEOMETRY_QA_V1`;
- all variants A-E must be present;
- every variant must hard-pass the R6 canonical geometry QA;
- IFC schema and geometry error counts must be zero;
- canonical room/IfcSpace match coverage and tolerances must pass;
- R6 never implies professional approval;
- R6 never implies `APPROVED_FOR_CONSTRUCTION`;
- existing BB34, BB35, security, documentation, support, version and
  release-request checks remain intact.

This binding does not override separate structural, permit, professional,
construction-release, legal, or domain-acceptance gates.
