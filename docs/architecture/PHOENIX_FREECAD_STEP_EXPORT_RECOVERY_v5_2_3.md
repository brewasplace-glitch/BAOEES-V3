# Phoenix FreeCAD STEP Export Recovery v5.2.3

## Confirmed state
- FreeCADCmd.exe is installed and found.
- The Phoenix macro runs.
- FCStd generation succeeds.
- STEP generation failed under the prior `Part.export(...)` route.

## Root cause
For this FreeCAD build, STEP exchange export must use the Import workbench API.
`Part.export(...)` is not the robust STEP writer path.

## Recovery
The acceptance macro now uses:

```python
import Import
Import.export([box], step_path)
```

Phoenix additionally verifies that the generated file:
- exists;
- is non-empty;
- begins with an ISO-10303-21 STEP header;
- receives a SHA-256 hash.

No simulated artifact can satisfy this acceptance gate.
