# Phoenix Unified Multi-Engine Production Orchestrator v6.1.0

## Purpose

v6.1.0 converts the qualified six-engine platform into a controlled production
orchestration layer.

## Central Digital Twin

Every project run starts from one project manifest and creates one immutable
Digital Twin snapshot. All engine routes read from or write back to that model.

## Engine responsibilities

- QGIS: site and geo context;
- FreeCAD: parametric native geometry and STEP;
- IfcOpenShell: IFC generation and BIM validation;
- CalculiX: verified linear-static FEA contract;
- OpenSees: structural-system analysis and equilibrium;
- EnergyPlus: design-day energy analysis with SQLite evidence.

## Production gate

The orchestrator first reruns the v6.0.4 six-engine qualification suite.
Production orchestration remains locked unless all six real engine tests pass,
simulated results remain disabled and the release gate is unlocked.

## Pilot

The included controlled pilot is Moskee Bunschoten:

- 7 m × 10 m;
- two storeys;
- 140 m² gross floor area.

The orchestrator may mark the engine chain as production-ready, but it does not
mark the project permit-ready while professional evidence requirements
REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108 remain open.
