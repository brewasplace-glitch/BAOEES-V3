"""Phoenix Sweet Home 3D adapter foundation v1.0."""
from pathlib import Path
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable
VERSION="1.0.0"
def capability_state(repository:Path)->dict:
    d=discover_executable("sweethome3d",repository)
    return {**d,"adapter_version":VERSION,"capabilities":["INTERIOR_LAYOUT","FURNITURE","INTERIOR_VISUALIZATION"]}
