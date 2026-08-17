"""PROJECT PHOENIX visual engine provisioning helpers v1.0."""
from __future__ import annotations
import json, os, shutil, subprocess, tempfile
from pathlib import Path

VERSION="1.0.0"

PACKAGE_IDS={
    "blender":"BlenderFoundation.Blender",
    "sweethome3d":"eTeks.SweetHome3D",
    "comfyui":"Comfy.ComfyUI-Desktop",
}

def winget_available()->bool:
    return shutil.which("winget") is not None

def winget_install(engine_id:str, timeout:int=1800)->dict:
    if engine_id not in PACKAGE_IDS:
        raise KeyError(engine_id)
    exe=shutil.which("winget")
    if not exe:
        return {"engine_id":engine_id,"attempted":False,"passed":False,"reason":"WINGET_NOT_AVAILABLE"}
    pkg=PACKAGE_IDS[engine_id]
    cmd=[
        exe,"install","--id",pkg,"--exact",
        "--accept-source-agreements","--accept-package-agreements",
        "--silent","--disable-interactivity"
    ]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    text=((p.stdout or "")+"\n"+(p.stderr or "")).strip()
    # winget commonly returns success also when package is already installed.
    return {
      "engine_id":engine_id,"package_id":pkg,"attempted":True,
      "returncode":p.returncode,"passed":p.returncode==0,
      "stdout":p.stdout,"stderr":p.stderr,"summary":" ".join(text.split())[:1000]
    }

def winget_list(engine_id:str, timeout:int=120)->dict:
    if engine_id not in PACKAGE_IDS: raise KeyError(engine_id)
    exe=shutil.which("winget")
    if not exe:return {"engine_id":engine_id,"listed":False,"reason":"WINGET_NOT_AVAILABLE"}
    pkg=PACKAGE_IDS[engine_id]
    p=subprocess.run([exe,"list","--id",pkg,"--exact","--accept-source-agreements"],capture_output=True,text=True,timeout=timeout)
    text=((p.stdout or "")+"\n"+(p.stderr or "")).strip()
    return {"engine_id":engine_id,"listed":p.returncode==0 and pkg.lower() in text.lower(),"returncode":p.returncode,"text":text[:2000]}

def blender_headless_smoke(blender_executable:Path, timeout:int=180)->dict:
    exe=Path(blender_executable).resolve()
    if not exe.exists():
        return {"passed":False,"reason":"BLENDER_EXECUTABLE_NOT_FOUND","executable":str(exe)}
    with tempfile.TemporaryDirectory(prefix="phoenix_blender_smoke_") as td:
        out=Path(td)/"phoenix_blender_smoke.txt"
        expr=(
          "from pathlib import Path;"
          f"Path(r'{str(out)}').write_text('PHOENIX_BLENDER_HEADLESS_OK', encoding='utf-8')"
        )
        p=subprocess.run(
          [str(exe),"--background","--factory-startup","--python-expr",expr],
          cwd=td,capture_output=True,text=True,timeout=timeout,
          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)
        )
        passed=p.returncode==0 and out.exists() and out.read_text(encoding="utf-8")=="PHOENIX_BLENDER_HEADLESS_OK"
        return {
          "passed":passed,"returncode":p.returncode,"executable":str(exe),
          "stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]
        }

def write_provisioning_state(target:Path, state:dict)->Path:
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return target
