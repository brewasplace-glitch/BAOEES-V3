# IfcOpenShell Python Detection Recovery v5.0.1

IfcOpenShell 0.8.5 was correctly installed as a Python module, while the v5.0.0
detector only searched for IfcConvert executables. The adapter now first imports
`ifcopenshell` using the active Phoenix Python interpreter and reports the module
as available. If that import fails, executable discovery remains the fallback.
