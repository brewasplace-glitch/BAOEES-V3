# QGIS Config Test Path Recovery v5.3.12

## Confirmed failure
The v5.3.11 implementation introduced the current configuration file:

`configs/phoenix/qgis_detector_evidence_based_availability_v5_3_11.json`

The inherited unit test still opened the removed legacy file:

`configs/phoenix/qgis_post_install_recovery_v5_3_3.json`

This caused a `FileNotFoundError` before the evidence-based detector could run.

## Recovery
v5.3.12 updates the test to the current configuration file and validates the
actual contract:

- schema `phoenix.qgis-detector-evidence-availability/5.3.11`;
- no QGIS installation action;
- existing installation reuse;
- exit code zero is sufficient;
- real accepted GeoPackage evidence is sufficient;
- batch exit code one with valid evidence is diagnostic only.

The test no longer depends on the removed v5.3.3 configuration path.

No QGIS installation or download occurs.
