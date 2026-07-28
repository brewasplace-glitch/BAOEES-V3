# Phoenix Open-Source Engine Adapter Layer v5.0.0

## Architecture rule
Phoenix orchestrates reliable domain engines instead of rebuilding them.

## Adapters
- IfcOpenShell / IfcConvert: IFC processing and conversion
- FreeCADCmd: parametric CAD automation
- EnergyPlus: building energy and thermal simulation
- OpenSees: structural and geotechnical analysis
- CalculiX CrunchiX: general finite element analysis
- QGIS Processing Executor: GIS and open-data processing

## Controls
Each adapter:
- discovers the executable through explicit environment variables or PATH;
- validates input extensions and required job fields;
- builds a reproducible command;
- captures stdout, stderr, exit code and duration;
- hashes generated outputs;
- writes a Phoenix run envelope;
- never fabricates results when an engine is missing;
- preserves professional review and release gates.

## Installation boundary
This package installs adapters, not third-party applications. Engine installation is
kept separate because package source, version, licence acceptance, administrator
rights and platform requirements differ by workstation.
