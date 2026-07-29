# Phoenix FreeCAD TopoShape STEP Recovery v5.2.4

## Confirmed diagnostic evidence
FreeCADCmd 1.1.1:
- executes the Phoenix macro;
- recomputes the model;
- creates the FCStd artifact;
- starts the STEP transfer writer;
- fails to create the STEP file through `Import.export(...)`.

The output folder and embedded path are valid because the FCStd artifact is
successfully written to the same directory.

## Recovery
The macro now exports directly from the model shape:

```python
box.Shape.exportStep(step_path)
```

This bypasses the generic Import workbench layer and calls the OpenCascade STEP
writer through the actual `Part::Box` TopoShape.

Phoenix still requires:
- a non-empty FCStd file;
- a non-empty STEP file;
- an ISO-10303-21 STEP header;
- SHA-256 for both artifacts;
- successful Phoenix FreeCAD detection.
