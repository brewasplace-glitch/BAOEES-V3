# Phoenix Architectural Output Directory Initialization Recovery v6.5.1

## Confirmed failure

v6.5.0 attempted to write the first floor-plan SVG before the `drawings`
directory existed. The pre-payload run therefore stopped before repository
mutation.

## Recovery

v6.5.1 initializes these directories immediately after creating the run root:

- `drawings`;
- `schedules`;
- `bim`.

The individual SVG, FreeCAD and IFC writers also create their own destination
directories defensively.

Before quality reporting and release-gate generation, the runner verifies that
all required SVG, CSV, FCStd, STEP, IFC and IFC-validation artifacts exist and
are non-empty.

No permit-ready or execution-ready safety rule is weakened.
