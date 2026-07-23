# Knowledge Graph Architecture

BB10 adds a semantic graph above the BB9 Digital Twin.

## Responsibilities

- Represent project objects, documents, requirements, sources and decisions as nodes
- Represent typed semantic relationships as edges
- Provide text, type and property queries
- Trace relationships across bounded graph depth
- Validate referential integrity and orphan nodes
- Import BB9 Digital Twin objects and relationships
- Persist graph state with deterministic JSON and SHA-256 evidence

The graph does not replace the Digital Twin. The Digital Twin remains the
authoritative project state; the Knowledge Graph adds semantic meaning,
traceability and query capability.
