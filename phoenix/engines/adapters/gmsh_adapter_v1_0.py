"""Phoenix Gmsh adapter foundation v1.0."""
from __future__ import annotations
import subprocess
from pathlib import Path
from phoenix.engines.engine_discovery_v1_0 import discover_engine

VERSION="1.0.0"

def capability_state(repository:Path)->dict:
    d=discover_engine("gmsh",repository)
    return {**d,"adapter_version":VERSION,"capabilities":["MESHING","GEOMETRY","MESH_CONVERSION"],"execution_supported":bool(d["available"])}

def mesh_geo(repository:Path,geo_file:Path,dimension:int=3,output:Path|None=None,timeout:int=300)->dict:
    state=capability_state(repository)
    if not state["available"]:raise RuntimeError("GMSH_ENGINE_NOT_AVAILABLE")
    geo=Path(geo_file).resolve()
    if not geo.exists():raise FileNotFoundError(geo)
    out=Path(output).resolve() if output else geo.with_suffix(".msh")
    cmd=[state["executable"],str(geo),f"-{int(dimension)}","-o",str(out)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    return {"engine":"gmsh","adapter_version":VERSION,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"output":str(out),"passed":p.returncode==0 and out.exists()}
