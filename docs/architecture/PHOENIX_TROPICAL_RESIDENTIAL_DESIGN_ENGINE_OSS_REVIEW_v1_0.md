# OSS review - Tropical Residential Design Engine Foundation v1.0
Review date: 2026-08-19.

- IfcOpenShell: primary IFC/BIM adapter; LGPL-3.0-or-later.
- FreeCAD: BIM/CAD fallback; LGPL-2.0-or-later.
- Shapely: primary 2D geometry; BSD-3-Clause.
- NetworkX: primary room adjacency; BSD-3-Clause.
- pymoo: optional multi-objective optimisation; Apache-2.0.
- EnergyPlus: future thermal/energy validation; free/open source.
- Blender: existing Phoenix visualization route.

Foundation custom code is limited to tropical heuristics, orchestration, scoring, Phoenix context/evidence and adapter contracts. No external package is installed silently.
