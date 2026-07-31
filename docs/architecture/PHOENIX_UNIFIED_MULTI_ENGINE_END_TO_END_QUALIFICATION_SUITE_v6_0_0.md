# Phoenix Unified Multi-Engine End-to-End Qualification Suite v6.0.0

This suite qualifies the six installed open-source engines in one controlled run:

- FreeCAD: real FCStd and STEP geometry;
- IfcOpenShell: real IFC4 create/write/reopen cycle;
- QGIS: real native buffer to GeoPackage;
- CalculiX: real linear-static C3D8 analysis;
- OpenSees: real linear-static 2D truss analysis;
- EnergyPlus: real design-day simulation with SQLite output.

Production release is unlocked only when all six engines pass. Every artifact is
hashed. Simulated results are prohibited. Professional review remains mandatory.
