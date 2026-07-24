# ADR-0006 — Offline-safe QGIS adapter

## Status

Accepted.

## Decision

The Phoenix QGIS integration must remain functional without requiring QGIS to
be installed in the standard Python environment.

## Consequences

- Core GIS models and project generation remain testable everywhere.
- Native PyQGIS functionality is optional and capability-detected.
- GIS workflows can fail clearly when a native-only operation is requested.
- QGIS installation paths are not hard-coded.
