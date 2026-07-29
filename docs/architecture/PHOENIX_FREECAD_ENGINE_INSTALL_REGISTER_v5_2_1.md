# Phoenix FreeCAD Engine Installation and Registration v5.2.1

## Recovery
Version 1.1.3 was incorrectly pinned in v5.2.0. It is not an available stable
FreeCAD release and WinGet cannot resolve it.

The corrected approved version is FreeCAD 1.1.1.

## Controlled installation
The installer:
1. queries WinGet for exact package `FreeCAD.FreeCAD`;
2. requires exact version 1.1.1 to be present;
3. installs or upgrades that exact version;
4. locates `FreeCADCmd.exe`;
5. configures `FREECAD_CMD`;
6. creates a real FCStd model and STEP export;
7. requires Phoenix detection to report FreeCAD as available;
8. commits and pushes only after all checks pass.
