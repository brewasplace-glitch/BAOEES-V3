# Phoenix BIM / IFC Synchronization Engine â€” Wave 13 v1.0

Wave 13 converts the verified Phoenix structural model and optional material
design results into a deterministic IFC-oriented exchange model.

It maps nodes, elements, materials, Phoenix identities and design evidence to
IFC entity intentions and Phoenix property sets. It also creates deterministic
GlobalId seeds and a complete SHA-256 source chain.

This version produces an auditable JSON exchange artifact that is ready for a
later IFC serializer. It does not write a binary or STEP IFC file, perform IFC
schema validation, create solid geometry, or verify round-trip behavior in BIM
authoring software.
