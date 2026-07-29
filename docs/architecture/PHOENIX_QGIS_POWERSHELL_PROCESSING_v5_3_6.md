# QGIS PowerShell Processing Recovery v5.3.6

QGIS version probing succeeds directly in PowerShell, while Python subprocess
execution of the OSGeo4W batch wrapper does not reliably forward Processing
arguments.

v5.3.6 therefore:
- prepares the EPSG:28992 GeoJSON with Python;
- invokes `qgis_process-qgis-ltr.bat` directly from PowerShell;
- runs `native:buffer`;
- captures stdout, stderr and exit code;
- validates the real GeoPackage with Python;
- requires the SQLite header and SHA-256 evidence;
- requires Phoenix detection to report QGIS available.

No QGIS installation or download occurs.
