"""PROJECT PHOENIX visual-design engine discovery v1.0."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

VERSION="1.0.0"

SPECS={
 "blender":{"executables":["blender.exe","blender"],"env":["BLENDER_HOME"]},
 "freecad":{"executables":["FreeCADCmd.exe","freecadcmd.exe","FreeCADCmd","freecadcmd","FreeCAD.exe","freecad.exe","FreeCAD","freecad"],"env":["FREECAD_HOME"]},
 "sweethome3d":{"executables":["SweetHome3D.exe","SweetHome3D","sweethome3d"],"env":["SWEETHOME3D_HOME"]},
}

def _scan(root:Path,names:set[str],depth:int=5)->Optional[Path]:
    if not root.exists(): return None
    try:
        if root.is_file() and root.name.lower() in names: return root.resolve()
        for current,dirs,files in os.walk(root):
            rel=Path(current).resolve().relative_to(root.resolve())
            if len(rel.parts)>=depth: dirs[:]=[]
            for f in files:
                if f.lower() in names:
                    return (Path(current)/f).resolve()
    except Exception:
        return None
    return None

def _roots(repository:Path)->list[Path]:
    repo=Path(repository).resolve()
    out=[repo/"tools",repo/"bin",repo/"apps",repo/"phoenix",repo]
    for key in ("PROGRAMFILES","PROGRAMFILES(X86)","LOCALAPPDATA"):
        raw=os.environ.get(key)
        if raw: out.append(Path(raw))
    home=Path.home()
    out += [home/"Blender",home/"FreeCAD",home/"SweetHome3D",Path("C:/Program Files"),Path("C:/Program Files (x86)")]
    seen=set();final=[]
    for p in out:
        s=str(p).lower()
        if s not in seen:
            seen.add(s);final.append(p)
    return final

def _version(engine_id:str,path:Path)->Optional[str]:
    """Probe only console-safe executables. Never launch GUI apps during discovery."""
    name=path.name.lower()
    if engine_id=="sweethome3d":
        return None
    if engine_id=="freecad":
        if "freecadcmd" not in name:
            return None
        commands=[["--version"],["-v"]]
    elif engine_id=="blender":
        commands=[["--version"]]
    else:
        return None
    with tempfile.TemporaryDirectory(prefix="phoenix_visual_probe_") as td:
        for args in commands:
            try:
                p=subprocess.run(
                    [str(path),*args],
                    cwd=td,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)
                )
                text=" ".join(((p.stdout or "")+" "+(p.stderr or "")).strip().split())
                if text:return text[:500]
            except Exception:
                pass
    return None

def discover_executable(engine_id:str,repository:Path)->dict:
    spec=SPECS[engine_id];names={n.lower() for n in spec["executables"]}
    for n in spec["executables"]:
        p=shutil.which(n)
        if p:return _result(engine_id,Path(p),"PATH")
    for key in spec["env"]:
        raw=os.environ.get(key)
        if raw:
            found=_scan(Path(raw),names,4)
            if found:return _result(engine_id,found,f"ENV:{key}")
    for root in _roots(repository):
        found=_scan(root,names,6 if Path(root).resolve()==Path(repository).resolve() else 5)
        if found:
            src="REPOSITORY_SCAN" if str(found).lower().startswith(str(Path(repository).resolve()).lower()) else "WINDOWS_LOCATION_SCAN"
            return _result(engine_id,found,src)
    return {"engine_id":engine_id,"available":False,"executable":None,"discovery_source":"NOT_FOUND","version":None}

def _result(engine_id,path,source):
    path=Path(path).resolve()
    name=path.name.lower()
    automation=True
    gui=False
    if engine_id=="freecad":
        automation="freecadcmd" in name
        gui=not automation
    elif engine_id=="sweethome3d":
        automation=False
        gui=True
    return {
      "engine_id":engine_id,
      "available":True,
      "executable":str(path),
      "discovery_source":source,
      "version":_version(engine_id,path),
      "automation_executable":automation,
      "gui_executable":gui
    }

def discover_comfyui(repository:Path)->dict:
    url=os.environ.get("COMFYUI_URL","http://127.0.0.1:8188").rstrip("/")
    home=os.environ.get("COMFYUI_HOME")
    roots=[]
    if home:roots.append(Path(home))
    repo=Path(repository).resolve()
    roots += [repo/"tools"/"ComfyUI",repo/"apps"/"ComfyUI",Path.home()/"ComfyUI",Path("C:/ComfyUI")]
    found_home=None
    for r in roots:
        if (r/"main.py").exists():
            found_home=r.resolve();break
    api=False
    try:
        with urllib.request.urlopen(url+"/system_stats",timeout=1.5) as response:
            api=200 <= response.status < 300
    except Exception:
        api=False
    return {
      "engine_id":"comfyui",
      "available":bool(found_home or api),
      "home":str(found_home) if found_home else None,
      "api_available":api,
      "url":url,
      "discovery_source":"API" if api else ("ENV_OR_FILESYSTEM" if found_home else "NOT_FOUND"),
      "version":None
    }

def discover_visual_stack(repository:Path)->dict:
    engines={eid:discover_executable(eid,repository) for eid in ("blender","freecad","sweethome3d")}
    engines["comfyui"]=discover_comfyui(repository)
    return {
      "schema_version":"phoenix.visual-design-engine-state/1.0",
      "version":VERSION,
      "engines":engines,
      "blender_ready":engines["blender"]["available"],
      "freecad_ready":engines["freecad"]["available"],
      "sweethome3d_ready":engines["sweethome3d"]["available"],
      "comfyui_ready":engines["comfyui"]["available"]
    }

def write_state(repository:Path,target:Path)->dict:
    state=discover_visual_stack(repository)
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    return state
