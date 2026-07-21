# Phoenix Structural Analysis Bootstrap Adapter â€” Wave 7 v1.0

Wave 7 connects the verified foundation artifact to the structural stage.

The adapter registers:

- nodes and three-dimensional coordinates;
- materials and material provenance;
- structural elements and connectivity;
- load cases;
- load combinations;
- a preliminary global degree-of-freedom count;
- solver-adapter readiness.

The adapter validates all element-to-material, element-to-node and
combination-to-load-case references.

It deliberately does not calculate or claim:

- reactions;
- displacements;
- member forces;
- convergence;
- stability;
- second-order effects;
- code compliance;
- member capacity.

A registered structural model therefore remains a bootstrap model until a
verified solver adapter and code-policy layer have executed.
