# Multi-Engine CalculiX SPOOLES Contract Recovery v6.0.2

## Confirmed failure

The unified suite used the generic CalculiX step:

`*STATIC`

The installed Windows/MSYS2 build had already been proven reliable only with
the standalone Phoenix contract:

`*STATIC,SOLVER=SPOOLES`

The generic solver path ended with Windows native exit code `3221225477`
(`0xC0000005`).

## Recovery

v6.0.2 reuses the proven CalculiX contract:

- executable: `C:\msys64\mingw64\bin\ccx.exe`;
- MSYS2 runtime directory prepended to `PATH`;
- `OMP_NUM_THREADS=1`;
- solver: `SPOOLES`;
- invocation: `ccx.exe -i qualification`;
- required non-empty `.dat` and `.frd` results.

No engine is reinstalled. All six real qualifications must still pass before
the production release gate is unlocked.
