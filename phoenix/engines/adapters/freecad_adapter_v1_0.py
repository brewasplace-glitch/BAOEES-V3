"""Phoenix FreeCAD adapter foundation v1.0."""
from pathlib import Path
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable
VERSION="1.0.0"
def capability_state(repository:Path)->dict:
    d=discover_executable("freecad",repository)
    return {**d,"adapter_version":VERSION,"capabilities":["PARAMETRIC_CAD","STEP","BIM_REVIEW"]+(["HEADLESS_AUTOMATION"] if d.get("automation_executable") else [])+(["GUI_REVIEW"] if d.get("gui_executable") else []),"headless_automation_supported":bool(d.get("automation_executable")),"gui_review_supported":bool(d.get("gui_executable"))}
