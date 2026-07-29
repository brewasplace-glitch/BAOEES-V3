# QGIS Confirmed Version Handoff v5.3.5

The QGIS batch wrapper prints valid version information when invoked directly
from PowerShell, but Python subprocess capture receives no parseable version
text and a wrapper-specific exit code 1.

Phoenix now separates responsibilities:

1. PowerShell invokes the confirmed QGIS wrapper directly.
2. PowerShell captures and parses `QGIS 3.44.12`.
3. The confirmed version is handed to the Python acceptance runner.
4. Python runs the real `native:buffer` operation.
5. Acceptance requires a non-empty GeoPackage with a valid SQLite header.
6. Raw processing exit codes remain recorded.
7. Simulated GIS output remains prohibited.

No QGIS installation or download occurs.
