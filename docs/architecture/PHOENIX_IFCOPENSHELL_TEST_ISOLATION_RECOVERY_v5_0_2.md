# IfcOpenShell Test Isolation Recovery v5.0.2

## Root cause
The v5.0.0 regression test assumed all engines were absent. After IfcOpenShell
0.8.5 was legitimately installed, the updated detector correctly reported it as
available, making the old test fail.

## Recovery
The missing-engine test is now isolated from the actual workstation by mocking:
- executable lookup;
- environment variables;
- IfcOpenShell Python-module detection.

Separate tests verify:
- Python-module detection takes precedence;
- IfcConvert executable detection remains the fallback.

The production detector itself was correct; only the legacy test contract was
outdated.
