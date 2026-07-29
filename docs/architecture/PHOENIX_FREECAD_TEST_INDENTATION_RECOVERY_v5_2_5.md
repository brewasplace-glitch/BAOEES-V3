# Phoenix FreeCAD Test Indentation Recovery v5.2.5

## Root cause
The v5.2.4 package contained the correct TopoShape STEP macro, but the related
unit test had one assertion indented eight spaces too far. Python therefore
raised `IndentationError: unexpected indent` before any FreeCAD acceptance run.

## Recovery
- The test indentation is corrected.
- The package statically compiles the test before installation.
- The macro remains `box.Shape.exportStep(step_path)`.
- FCStd, STEP, ISO-10303-21 and SHA-256 acceptance gates remain unchanged.
