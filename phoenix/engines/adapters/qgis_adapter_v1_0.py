"""Phoenix QGIS/PyQGIS adapter foundation v1.0."""
from __future__ import annotations
import subprocess
from pathlib import Path
from phoenix.engines.engine_discovery_v1_0 import discover_engine

VERSION="1.0.0"

def capability_state(repository:Path)->dict:
    d=discover_engine("qgis",repository)
    exe=(d.get("executable") or "").lower()
    return {**d,"adapter_version":VERSION,"capabilities":["GIS","SPATIAL_ANALYSIS","CARTOGRAPHY","PROCESSING"],"processing_cli":bool("qgis_process" in exe)}

def list_algorithms(repository:Path,timeout:int=60)->dict:
    state=capability_state(repository)
    if not state["available"]:raise RuntimeError("QGIS_ENGINE_NOT_AVAILABLE")
    if not state["processing_cli"]:raise RuntimeError("QGIS_PROCESS_CLI_NOT_AVAILABLE")
    p=subprocess.run([state["executable"],"list"],capture_output=True,text=True,timeout=timeout)
    return {"engine":"qgis","adapter_version":VERSION,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"passed":p.returncode==0}
