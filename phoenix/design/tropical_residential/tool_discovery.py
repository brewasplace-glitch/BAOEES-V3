from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional


def _first_existing(candidates: List[str]) -> Optional[str]:
    seen = set()
    for item in candidates:
        if not item:
            continue
        for expanded in glob.glob(os.path.expandvars(item)):
            p = str(Path(expanded))
            key = p.lower()
            if key in seen:
                continue
            seen.add(key)
            if Path(p).is_file():
                return str(Path(p).resolve())
    return None


def discover_freecad() -> Optional[str]:
    candidates = [
        os.environ.get("PHOENIX_FREECAD_EXE", ""),
        shutil.which("FreeCADCmd") or "",
        shutil.which("FreeCADCmd.exe") or "",
        r"%ProgramFiles%\FreeCAD*\bin\FreeCADCmd.exe",
        r"%ProgramFiles%\FreeCAD *\bin\FreeCADCmd.exe",
        r"%LOCALAPPDATA%\Programs\FreeCAD*\bin\FreeCADCmd.exe",
        r"%LOCALAPPDATA%\Programs\FreeCAD *\bin\FreeCADCmd.exe",
    ]
    return _first_existing(candidates)


def discover_blender() -> Optional[str]:
    candidates = [
        os.environ.get("PHOENIX_BLENDER_EXE", ""),
        shutil.which("blender") or "",
        shutil.which("blender.exe") or "",
        r"%ProgramFiles%\Blender Foundation\Blender*\blender.exe",
        r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender*\blender.exe",
        r"%LOCALAPPDATA%\Programs\Blender*\blender.exe",
    ]
    return _first_existing(candidates)


def discover_tools() -> Dict[str, Dict[str, object]]:
    f = discover_freecad()
    b = discover_blender()
    return {
        "freecad": {
            "found": bool(f), "executable": f,
            "role": "BIM_CAD_REFINEMENT_FALLBACK", "license_family": "LGPL-2.1-or-later"
        },
        "blender": {
            "found": bool(b), "executable": b,
            "role": "3D_VISUAL_HANDOFF", "license_family": "GPL"
        },
    }
