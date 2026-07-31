# Multi-Engine IfcOpenShell Dedicated Python Runtime Recovery v6.0.1

## Confirmed failure

The general orchestration Python runtime did not contain IfcOpenShell, while
IfcOpenShell was already installed and verified in another Python runtime.

## Recovery

v6.0.1 routes the IFC qualification through a dedicated interpreter:

1. `IFCOPENSHELL_PYTHON`, when configured;
2. the known Phoenix-compatible Python 3.14 installation;
3. other verified Python application candidates.

Each candidate must pass:

`import ifcopenshell; print(ifcopenshell.version)`

The IFC4 create/write/reopen workflow is then executed in a separate Python
process through that exact interpreter. OpenSees continues to use its own
dedicated Python 3.12 virtual environment.

No engine is reinstalled. Production release remains locked unless all six
real qualifications pass.
