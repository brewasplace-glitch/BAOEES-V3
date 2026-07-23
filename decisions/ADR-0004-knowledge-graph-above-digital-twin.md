# ADR-0004 — Knowledge Graph above the Digital Twin

## Status

Accepted.

## Decision

The Knowledge Graph is a semantic layer above the BB9 Digital Twin rather than
a replacement database.

## Consequences

- The Digital Twin remains the authoritative operational state.
- The graph can evolve independently for search and reasoning.
- Graph nodes retain references to originating Digital Twin objects.
- Future AI workflows can query traceable relationships without mutating core state.
