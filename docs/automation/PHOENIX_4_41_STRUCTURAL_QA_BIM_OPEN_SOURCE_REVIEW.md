# PHOENIX 4.41 — Structural QA / BIM open-source review

## Primary BIM engine — IfcOpenShell 0.8.5

IfcOpenShell 0.8.5 is used for IFC4 creation and read-back validation.
The package is LGPLv3+ and provides a Windows Python 3.14 wheel.

## QA companion — IfcTester 0.8.5

IfcTester is used for Information Delivery Specification (IDS) authoring and validation of the IFC handoff.
It can validate IFC models against IDS requirements and generate reports.

## Secondary BIM consumer / fallback path — FreeCAD 1.1.3

FreeCAD 1.1.3 remains the preferred open-source desktop BIM/CAD consumer for manual/visual inspection where a GUI workflow is wanted.
Phoenix does not make FreeCAD a blocking runtime dependency in this stage.

## Existing visual fallback

The prior-stage GLB/OBJ/STL model remains the independent visual coordination representation if an IFC viewer is unavailable.

No BIM export or IDS PASS unlocks construction release while mandatory engineering holds remain open.


## FIX R1 — runtime interoperability

Cross-stage QA must be able to import the dependencies of the stage being re-verified. The QA/BIM runner therefore combines the IfcOpenShell/IfcTester runtime with a dedicated 3D verification runtime containing trimesh, python-docx and pypdf.

The compatibility bridge only reads/verifies prior evidence; it does not rewrite the prior 3D/report output.


## FIX R2 — native IfcTester report serialization

Phoenix now delegates JSON serialization to `ifctester.reporter.Json.to_file()`.
This is the IfcTester 0.8.5 library-supported path and correctly encodes IFC entity references in reporter results.
Phoenix then parses the resulting JSON file for the boolean validation status.
