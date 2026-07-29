# QGIS CMD Wrapper Quoting Recovery v5.3.7

## Confirmed failure
The v5.3.6 PowerShell installer reached the direct QGIS Processing step, but the
single dynamically assembled `cmd.exe /c` command line contained invalid nested
quotes. Windows therefore returned:

`De syntaxis van de bestandsnaam, mapnaam of volumenaam is onjuist.`

## Recovery
v5.3.7 creates a short temporary `.cmd` file containing one deterministic QGIS
Processing command. All paths are quoted once in native CMD syntax.

Workflow:
1. PowerShell confirms QGIS 3.44.12.
2. Python creates the EPSG:28992 GeoJSON input.
3. PowerShell writes a temporary CMD wrapper.
4. CMD calls `qgis_process-qgis-ltr.bat run native:buffer`.
5. Stdout, stderr and exit code are captured.
6. Python requires a real, non-empty GeoPackage with SQLite header.
7. Phoenix detection must report QGIS available.
8. Commit and push occur only after all controls pass.

No QGIS installation or download occurs.
