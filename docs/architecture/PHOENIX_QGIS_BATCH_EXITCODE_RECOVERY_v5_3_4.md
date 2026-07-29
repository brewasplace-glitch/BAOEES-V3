# QGIS Batch Exit-Code Recovery v5.3.4

## Confirmed behavior
The installed QGIS 3.44.12 batch launcher prints correct version information when
run manually. Through Python's `subprocess`, the same batch wrapper can return
exit code 1 despite producing valid QGIS output.

## Recovery
Phoenix now:
- invokes the batch file through `cmd.exe /d /c` without an extra `call`;
- parses and validates the QGIS 3.44 version output;
- records the raw version-probe exit code;
- runs the real `native:buffer` operation;
- records the raw processing exit code;
- accepts only when a non-empty GeoPackage with a valid SQLite header exists;
- hashes the real input and output artifacts;
- never accepts simulated output.

The actual artifact is authoritative; a wrapper-specific exit code cannot
override valid generated evidence.
