# OpenSees Dedicated Python 3.12 Runtime Recovery v5.5.5

## Confirmed failure

OpenSeesPy 3.8.0.0 installed under Python 3.14, but the native Windows module
failed to load with a DLL import error.

## Runtime contract

Phoenix now uses a dedicated Python 3.12 x64 environment:

`C:\PHOENIX-ENGINES\OpenSeesPy\3.8.0.0\venv`

The environment contains:

- `openseespy==3.8.0.0`
- `openseespywin==3.8.0.0`

The registered interpreter is:

`C:\PHOENIX-ENGINES\OpenSeesPy\3.8.0.0\venv\Scripts\python.exe`

## Safety and acceptance

1. Reuse an existing Python 3.12 x64 runtime when available.
2. Otherwise install `Python.Python.3.12` through Windows Package Manager.
3. Create or repair the dedicated virtual environment.
4. Install pinned OpenSeesPy packages.
5. Require a successful native import and `ops.version()` probe.
6. Run the real two-element 2D truss analysis before repository mutation.
7. Copy the Phoenix adapter payload only after external runtime verification.
8. Repeat tests and acceptance from the repository.
9. Require `opensees: AVAILABLE`.
10. Commit and push only after every validation gate passes.

No third-party runtime or wheel is committed to Git.
