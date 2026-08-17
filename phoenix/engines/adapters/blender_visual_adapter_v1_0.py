"""Phoenix Blender visual adapter v1.0."""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable
from phoenix.engines.ifc_visual_mesh_adapter_v1_0 import ifc_to_obj

VERSION="1.0.0"

def capability_state(repository:Path)->dict:
    d=discover_executable("blender",repository)
    return {**d,"adapter_version":VERSION,"capabilities":["IFC_DERIVED_RENDERING","EXTERIOR","INTERIOR","ANIMATION"]}

def render_ifc(repository:Path,ifc_path:Path,output_png:Path,timeout:int=600)->dict:
    state=capability_state(repository)
    if not state["available"]:raise RuntimeError("BLENDER_ENGINE_NOT_AVAILABLE")
    output_png=Path(output_png).resolve();output_png.parent.mkdir(parents=True,exist_ok=True)
    obj=output_png.with_suffix(".obj")
    mesh=ifc_to_obj(ifc_path,obj)
    script=Path(__file__).with_name("blender_phoenix_render_script_v1_0.py")
    p=subprocess.run([state["executable"],"--background","--python",str(script),"--",str(obj),str(output_png)],capture_output=True,text=True,timeout=timeout)
    result={"engine":"blender","adapter_version":VERSION,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"output":str(output_png),"passed":p.returncode==0 and output_png.exists(),"mesh_evidence":mesh}
    output_png.with_suffix(".render.evidence.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result
