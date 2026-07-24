# ADR-0007 — OpenSees offline verification mode

## Status

Accepted.

## Decision

BB13 includes a small deterministic offline truss solver while OpenSeesPy
remains an optional runtime dependency.

## Consequences

- installation and integration tests work without OpenSeesPy;
- native OpenSeesPy is used when available;
- unsupported advanced analyses fail explicitly;
- engineering scope remains traceable.
