# Phoenix Core v2.0 — BB5 IfcOpenShell BIM Integration Engine v1.0.0

## Purpose

BB5 upgrades the IfcOpenShell foundation adapter to an operational BIM
integration engine for IFC reading, writing, validation, querying, property-set
processing and Digital Twin export.

## Delivered

- IfcOpenShell module and version detection;
- IFC model summary;
- entity queries by IFC class;
- property-set extraction;
- spatial structure extraction;
- validation integration;
- basic IFC file creation;
- normalized Digital Twin export;
- atomic JSON output;
- SHA-256 evidence;
- BB3 lifecycle and Digital Twin write-back compatibility.

## Operational boundary

The package does not install third-party software. Runtime execution requires
the `ifcopenshell` Python package in the Phoenix environment. Automated tests
use a deterministic simulated module.

## Progress

Phoenix Core v2.0 overall progress after BB5: **32%**.
