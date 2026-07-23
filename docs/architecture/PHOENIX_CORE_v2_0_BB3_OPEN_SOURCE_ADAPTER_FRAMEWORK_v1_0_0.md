# Phoenix Core v2.0 — BB3 Open Source Adapter Framework v1.0.0

## Purpose

BB3 introduces a uniform adapter lifecycle for external open-source
applications and a controlled write-back contract to the Phoenix Digital Twin.

## Delivered

- adapter lifecycle states;
- initialization, readiness, execution and shutdown;
- health-check contract;
- input and output contracts;
- adapter registry;
- capability-based adapter lookup;
- managed execution envelope;
- SHA-256 audit evidence;
- Digital Twin write-back contract;
- initial foundation adapters for FreeCAD, IfcOpenShell, Blender and QGIS.

## Safety boundary

The four built-in adapters are foundation adapters. They can identify
dependencies and expose capabilities, but real engineering execution is
deliberately blocked until application-specific integration Build Blocks are
completed.

## Progress

Phoenix Core v2.0 overall progress after BB3: **18%**.
