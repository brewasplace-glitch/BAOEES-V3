# Phoenix FreeCAD Engine Macro Output Recovery v5.2.2

## Confirmed state
FreeCAD 1.1.1 is already installed. The package identity and static Phoenix tests
passed.

## Root cause
`FreeCADCmd.exe` does not reliably expose trailing command-line values to a
FreeCAD Python macro through `sys.argv` in the same way as the system Python
interpreter. The acceptance macro therefore did not receive the requested
output directory.

## Recovery
Phoenix now:
1. resolves the absolute acceptance output directory;
2. creates a temporary FreeCAD runtime macro;
3. embeds that absolute directory directly into the runtime macro;
4. invokes FreeCADCmd with only the generated macro path;
5. runs the macro with the output directory as working directory;
6. preserves stdout and stderr on failure;
7. requires non-empty FCStd and STEP artifacts;
8. records SHA-256 hashes before accepting FreeCAD.

The existing FreeCAD installation is reused. Installation is attempted only when
FreeCADCmd.exe cannot be found.
