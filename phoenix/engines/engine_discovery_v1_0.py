"""PROJECT PHOENIX open-source engine discovery v1.0."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional

VERSION="1.0.0"

ENGINE_SPECS={
 "calculix":{"executables":["ccx.exe","ccx"],"env":["CCX_HOME","CALCULIX_HOME"]},
 "gmsh":{"executables":["gmsh.exe","gmsh"],"env":["GMSH_HOME"]},
 "qgis":{"executables":["qgis_process.exe","qgis_process","qgis-bin.exe","qgis.exe"],"env":["QGIS_PREFIX_PATH","OSGEO4W_ROOT"]},
}

def _candidate_file(path:Path,names:set[str])->Optional[Path]:
    try:
        if path.is_file() and path.name.lower() in names:
            return path.resolve()
    except OSError:
        pass
    return None

def _scan_root(root:Path,names:set[str],max_depth:int=5)->Optional[Path]:
    if not root.exists():
        return None
    root=root.resolve()
    direct=_candidate_file(root,names)
    if direct:return direct
    try:
        for current,dirs,files in os.walk(root):
            rel=Path(current).relative_to(root)
            if len(rel.parts)>=max_depth:
                dirs[:]=[]
            for f in files:
                if f.lower() in names:
                    return (Path(current)/f).resolve()
    except (OSError,PermissionError):
        return None
    return None

def _windows_roots(engine:str,repository:Path)->list[Path]:
    roots=[repository]
    home=Path.home()
    local=os.environ.get("LOCALAPPDATA")
    program=os.environ.get("PROGRAMFILES")
    program86=os.environ.get("PROGRAMFILES(X86)")
    system_drive=os.environ.get("SystemDrive","C:")
    if local:roots.append(Path(local))
    if program:roots.append(Path(program))
    if program86:roots.append(Path(program86))
    roots.extend([
      Path(system_drive+"/CalculiX"),
      Path(system_drive+"/ccx"),
      Path(system_drive+"/gmsh"),
      Path(system_drive+"/QGIS"),
      Path(system_drive+"/OSGeo4W"),
      home/"CalculiX",home/"gmsh",home/"QGIS"
    ])
    # High-value Phoenix locations first.
    roots[0:0]=[
      repository/"tools",repository/"bin",repository/"solvers",
      repository/"phoenix",repository/"apps"
    ]
    seen=[];out=[]
    for r in roots:
        s=str(r).lower()
        if s not in seen:
            seen.append(s);out.append(r)
    return out

def _from_env(spec:dict,names:set[str])->Optional[tuple[Path,str]]:
    for key in spec.get("env",[]):
        raw=os.environ.get(key)
        if not raw:continue
        p=Path(raw)
        if p.is_file() and p.name.lower() in names:
            return p.resolve(),f"ENV:{key}"
        found=_scan_root(p,names,max_depth=4)
        if found:return found,f"ENV:{key}"
    return None

def discover_engine(engine_id:str,repository:Path)->dict:
    if engine_id not in ENGINE_SPECS:
        raise KeyError(engine_id)
    repository=Path(repository).resolve()
    spec=ENGINE_SPECS[engine_id]
    names={n.lower() for n in spec["executables"]}

    for name in spec["executables"]:
        p=shutil.which(name)
        if p:
            return _result(engine_id,Path(p).resolve(),"PATH")

    env=_from_env(spec,names)
    if env:
        return _result(engine_id,env[0],env[1])

    for root in _windows_roots(engine_id,repository):
        found=_scan_root(root,names,max_depth=6 if root==repository else 5)
        if found:
            source="REPOSITORY_SCAN" if str(found).lower().startswith(str(repository).lower()) else "WINDOWS_LOCATION_SCAN"
            return _result(engine_id,found,source)

    return {
      "engine_id":engine_id,"available":False,"executable":None,
      "discovery_source":"NOT_FOUND","version":None,
      "evidence":{"searched_path":True,"searched_environment":spec.get("env",[]),"repository":str(repository)}
    }

def _run_version(path:Path)->Optional[str]:
    commands=[
      [str(path),"--version"],
      [str(path),"-version"],
      [str(path),"-v"],
    ]
    # Some solver executables (notably CalculiX/ccx) interpret an unknown
    # version flag as a job name and emit .dat/.sta/.cvg files. Therefore
    # version probing is isolated in a temporary working directory.
    with tempfile.TemporaryDirectory(prefix="phoenix_engine_probe_") as td:
        for cmd in commands:
            try:
                p=subprocess.run(
                    cmd,
                    cwd=td,
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                text=(p.stdout or "")+"\n"+(p.stderr or "")
                text=" ".join(text.strip().split())
                if text:return text[:500]
            except Exception:
                pass
    return None

def _result(engine_id:str,path:Path,source:str)->dict:
    return {
      "engine_id":engine_id,"available":True,"executable":str(path),
      "discovery_source":source,"version":_run_version(path),
      "evidence":{"exists":path.exists(),"name":path.name,"parent":str(path.parent)}
    }

def discover_core(repository:Path)->dict:
    repository=Path(repository).resolve()
    states={k:discover_engine(k,repository) for k in ("calculix","gmsh","qgis")}
    return {
      "schema_version":"phoenix.engine-discovery-state/1.0",
      "discovery_version":VERSION,
      "repository":str(repository),
      "engines":states,
      "calculix_ready":states["calculix"]["available"],
      "gmsh_ready":states["gmsh"]["available"],
      "qgis_ready":states["qgis"]["available"]
    }

def write_discovery_state(repository:Path,target:Path)->dict:
    state=discover_core(repository)
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    return state
