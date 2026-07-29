import os

OUTPUT_DIR = r"__PHOENIX_OUTPUT_DIR__"
os.makedirs(OUTPUT_DIR, exist_ok=True)

import FreeCAD as App
import Part

doc = App.newDocument("PHOENIX_FREECAD_ACCEPTANCE")
box = doc.addObject("Part::Box", "PhoenixAcceptanceBox")
box.Label = "Phoenix Acceptance Box"
box.Length = 1000.0
box.Width = 800.0
box.Height = 600.0
doc.recompute()

fcstd_path = os.path.join(OUTPUT_DIR, "phoenix_freecad_acceptance.FCStd")
step_path = os.path.join(OUTPUT_DIR, "phoenix_freecad_acceptance.step")

doc.saveAs(fcstd_path)
box.Shape.exportStep(step_path)

if not os.path.isfile(fcstd_path):
    raise RuntimeError("FCStd file was not created")
if not os.path.isfile(step_path):
    raise RuntimeError("STEP file was not created")

print("PHOENIX FREECAD FCSTD CREATED:", fcstd_path)
print("PHOENIX FREECAD STEP CREATED:", step_path)
App.closeDocument(doc.Name)
