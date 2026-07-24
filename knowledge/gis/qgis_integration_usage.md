# QGIS Integration Usage

BB12 supports two runtime modes.

## Offline mode

Available everywhere. It provides:

- GIS project manifests;
- layer registration;
- GeoJSON handling;
- CRS and extent validation;
- basic spatial primitives;
- QGIS `.qgs` generation;
- Digital Twin and Knowledge Graph publication.

## Native mode

Activated when PyQGIS or `qgis_process` is available. Future Build Blocks can
use this mode for Processing algorithms, raster analysis and native QGIS export.

Project workflows must record the runtime mode in their evidence.
