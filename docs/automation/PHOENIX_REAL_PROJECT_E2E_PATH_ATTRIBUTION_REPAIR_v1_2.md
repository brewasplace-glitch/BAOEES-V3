# PROJECT PHOENIX — REAL-PROJECT E2E RUNTIME DISCOVERY PATH ATTRIBUTION REPAIR v1.2

## Bound baseline
`project-phoenix` @ `c747697b932a99575797e0522c52f5906e94db73`

## Reason for repair
Runtime discovery v1.1 proved that FreeCAD, Blender and CalculiX are available, but its
configured-path scanner could associate unrelated executable paths with a tool whenever
the surrounding source file mentioned that tool. That made the availability signal
useful, but the candidate lists unsafe for automatic execution.

Examples observed in v1.1:
- `FREECAD_PATH` included `ccx.exe`, Python, Git, SketchUp and SCIA paths.
- `BLENDER_PATH` included Python, Git and FreeCAD paths before the real Blender binary.
- `CALCULIX_PATH` included Python, Git, FreeCAD, SketchUp, SCIA and EnergyPlus paths.

## v1.2 rule
Candidate attribution is now based on the executable basename itself:
- FreeCAD: `FreeCADCmd(.exe)` or `FreeCAD(.exe)`
- Blender: `blender(.exe)`
- CalculiX: `ccx(.exe)` or versioned `ccx_*.exe`

Keyword proximity in another file is no longer sufficient.

Each accepted binary also receives a bounded version/info probe. No dependency is
installed and Playwright discovery still performs no `npx` fetch.

## Expected real binaries from v1.1 evidence
- FreeCAD: `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe`
- Blender: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
- CalculiX: at least `C:\Program Files\FreeCAD 1.1\bin\ccx.exe` and/or
  `C:\msys64\mingw64\bin\ccx.exe`

## Governance
Real-project selection remains explicit. Production and FOR CONSTRUCTION remain locked.
