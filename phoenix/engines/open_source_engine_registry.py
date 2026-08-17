"""PROJECT PHOENIX Open-Source Engine Registry v1.0."""
from __future__ import annotations
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from phoenix.engines.engine_discovery_v1_0 import discover_engine as _phoenix_discover_engine
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable as _phoenix_visual_discover_executable, discover_comfyui as _phoenix_visual_discover_comfyui

VERSION="1.0.0"

def _probe_python(module):
    try:
        m=importlib.import_module(module)
        return {"available":True,"version":str(getattr(m,"version",getattr(m,"__version__","unknown")))}
    except Exception as exc:
        return {"available":False,"error":f"{type(exc).__name__}: {exc}"}

def _which(names, repository=None):
    for name in names or []:
        p=shutil.which(name)
        if p:return p
    if repository:
        repo=Path(repository)
        wanted={str(n).lower() for n in names or []}
        for base in (repo/"tools",repo/"bin",repo/"solvers",repo/"phoenix",repo/"apps"):
            if not base.exists(): continue
            try:
                for candidate in base.rglob("*"):
                    if candidate.is_file() and candidate.name.lower() in wanted:
                        return str(candidate.resolve())
            except OSError:
                pass
    return None

def evaluate_registry(registry_path:Path):
    registry_path=Path(registry_path).resolve()
    data=json.loads(registry_path.read_text(encoding="utf-8-sig"))
    repository=registry_path.parents[2] if len(registry_path.parents)>=3 else None
    states=[]
    for e in data["engines"]:
        state={"id":e["id"],"name":e["name"],"tier":e["tier"],"capabilities":e.get("capabilities",[])}
        if e["id"]=="ifcopenshell":
            state.update(_probe_python("ifcopenshell"))
        else:
            # PHOENIX_DEEP_ENGINE_DISCOVERY_v1_0
            if e["id"] in {"calculix","gmsh","qgis"}:
                deep=_phoenix_discover_engine(e["id"],repository)
                state.update({
                  "available":deep["available"],
                  "executable":deep.get("executable"),
                  "version":deep.get("version"),
                  "discovery_source":deep.get("discovery_source"),
                  "discovery_evidence":deep.get("evidence",{})
                })
                if not deep["available"]:
                    state["status_note"]="REGISTERED_BUT_NOT_DISCOVERED"
            # PHOENIX_VISUAL_DESIGN_STACK_v1_0
            elif e["id"] in {"blender","freecad","sweethome3d"}:
                deep=_phoenix_visual_discover_executable(e["id"],repository)
                state.update(deep)
                if not deep["available"]:
                    state["status_note"]="REGISTERED_BUT_NOT_DISCOVERED"
            elif e["id"]=="comfyui":
                deep=_phoenix_visual_discover_comfyui(repository)
                state.update(deep)
                if not deep["available"]:
                    state["status_note"]="REGISTERED_BUT_NOT_DISCOVERED"
            else:
                exe=_which(e.get("executables",[]),repository)
                state["available"]=bool(exe)
                if exe:state["executable"]=exe
                if not exe:state["status_note"]="REGISTERED_NOT_REQUIRED_FOR_CURRENT_DISCIPLINE"
        states.append(state)
    required=[s for s in states if s["tier"]=="REQUIRED_CORE"]
    return {
      "schema_version":"phoenix.open-source-engine-state/1.0",
      "registry_version":data["registry_version"],
      "states":states,
      "required_core_all_available":all(s["available"] for s in required),
      "ifc_authoritative_ready":next((s["available"] for s in states if s["id"]=="ifcopenshell"),False)
    }

def write_state(registry_path:Path,output_path:Path):
    state=evaluate_registry(registry_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    return state
