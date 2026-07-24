# QGIS Integration Architecture

BB12 is the GIS integration layer of Project Phoenix.

## Design

- Offline-safe core that works without a local QGIS installation
- Optional discovery of PyQGIS and `qgis_process`
- Provider-neutral layer registry
- QGIS-compatible `.qgs` project generation
- Deterministic Phoenix GIS manifest
- Digital Twin publication
- Knowledge Graph publication
- GIS service catalog for WMS, WFS, WMTS and XYZ endpoints

Network connectors and jurisdiction-specific catalog entries are registered
through configuration. They are not hard-coded into the engine.
