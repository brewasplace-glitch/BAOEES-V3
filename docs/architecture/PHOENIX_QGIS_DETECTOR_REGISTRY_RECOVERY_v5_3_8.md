# QGIS Detector Registry Recovery v5.3.8

## Confirmed state
The real QGIS acceptance run succeeded:
- QGIS 3.44.12 detected;
- `native:buffer` executed;
- process exit code 0;
- valid GeoPackage created;
- acceptance status `ACCEPTED`.

The remaining failure is isolated to the Phoenix engine registry. The generic
detector still instantiated the legacy QGIS adapter and therefore reported
`qgis: NOT FOUND`.

## Recovery
v5.3.8:
1. preserves the successful QGIS installation;
2. preserves the real acceptance evidence;
3. activates `QGISWindowsAdapter` across supported registry shapes;
4. verifies the adapter is referenced beyond its import;
5. reruns Phoenix engine detection;
6. requires the detected executable to be
   `C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat`;
7. commits and pushes only after `qgis: AVAILABLE`.

No QGIS installation or download occurs.
