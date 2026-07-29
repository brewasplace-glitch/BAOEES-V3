# QGIS Detector Evidence-Based Availability Recovery v5.3.11

## Confirmed state
QGIS 3.44.12 is installed and operational. The real acceptance run has:

- status `ACCEPTED`;
- algorithm `native:buffer`;
- processing exit code `0`;
- a real non-empty GeoPackage;
- acceptance basis `REAL_VALID_GEOPACKAGE_ARTIFACT`;
- `simulated: false`.

The generic Phoenix detector still reported QGIS unavailable because the
Windows batch wrapper's separate version probe returns exit code 1.

## Recovery policy
QGIS is available when either:

1. the direct version probe succeeds; or
2. the launcher exists and a matching real acceptance record proves:
   - QGIS 3.44 LTR;
   - status `ACCEPTED`;
   - non-simulated execution;
   - real valid GeoPackage evidence;
   - the same launcher path.

A non-zero wrapper version-probe code remains in `notes` for diagnostics, but
does not override stronger real execution evidence.

No QGIS installation or download occurs.
