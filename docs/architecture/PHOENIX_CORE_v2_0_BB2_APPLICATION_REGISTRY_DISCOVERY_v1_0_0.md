# Phoenix Core v2.0 — BB2 Application Registry & Discovery Service v1.0.0

## Purpose

BB2 adds automatic discovery of locally available open-source applications and
updates the OSIF application registry with executable, module, version, health,
capability and evidence data.

## Delivered

- native executable discovery through the operating-system path;
- Python-module discovery;
- version probing with bounded timeout;
- health status classification;
- capability indexing;
- registry upsert behavior;
- atomic discovery-report writing;
- SHA-256 discovery evidence;
- default discovery catalog for IfcOpenShell, FreeCAD, Blender and QGIS;
- command-line discovery runner.

## Safety boundary

BB2 only discovers applications. It does not install software and does not yet
execute discipline workflows through these applications.

## Progress

Phoenix Core v2.0 overall progress after BB2: **12%**.
