# CalculiX MSYS2 Runtime Path Recovery v5.4.6

## Confirmed state
MSYS2 package `mingw-w64-x86_64-calculix-ccx 2.23-1` is installed and
`C:\msys64\mingw64\bin\ccx.exe` exists.

The direct Windows/Python solver launch returned exit code 201 because the
MinGW runtime directory was not guaranteed to be first in `PATH`.

## Recovery
v5.4.6:
1. prepends `C:\msys64\mingw64\bin` to the subprocess `PATH`;
2. performs a real launcher probe;
3. records probe stdout, stderr and exit code;
4. runs the same real C3D8 static model;
5. requires solver exit code 0;
6. requires real DAT and FRD results;
7. requires Phoenix detection `calculix: AVAILABLE`;
8. commits and pushes only after all controls pass.

No third-party binary is committed to Git.
