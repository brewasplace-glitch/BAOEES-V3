# OpenSees PowerShell Python Launcher Recovery v5.5.1

## Confirmed failure
The v5.5.0 installer failed before OpenSeesPy installation because PowerShell
did not accept `$g.Source` directly after the call operator `&`.

## Recovery
v5.5.1:
1. stores the discovered launcher path in a separate launcher variable;
2. invokes `py.exe -3` through that variable;
3. resolves the actual Python executable with `sys.executable`;
4. trims and validates the resolved Python executable path;
5. refuses to start pip if the resolved path does not exist;
6. keeps repository rollback disabled before payload copy;
7. preserves the full OpenSeesPy installation, acceptance, detector, commit,
   push and final clean/synchronized gates.

No repository mutation occurs before Python resolution and OpenSeesPy import
verification succeed.
