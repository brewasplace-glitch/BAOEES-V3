from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .tool_discovery import discover_freecad


_FREECAD_SCRIPT = r"""
import json, math, sys
import FreeCAD as App
import Part

if len(sys.argv) < 3:
    raise RuntimeError("Phoenix FreeCAD bridge requires layout_json and output_fcstd arguments")

layout_path=sys.argv[-2]
out_path=sys.argv[-1]
layout=json.load(open(layout_path,'r',encoding='utf-8'))

doc=App.newDocument('PHOENIX_TROPICAL_RESIDENTIAL')
raised=float(layout['elevation']['raised_floor_m'])
storey_h=float(layout['storey_height_m'])

for s in range(int(layout['storeys'])):
    z=raised+s*storey_h-0.20
    slab=doc.addObject('Part::Feature',f'Slab_S{s+1}')
    slab.Shape=Part.makeBox(
        float(layout['footprint']['width_m']),
        float(layout['footprint']['depth_m']),
        0.20,
        App.Vector(0,0,z)
    )

for idx,w in enumerate(layout['walls']):
    x1,y1,x2,y2=map(float,(w['x1'],w['y1'],w['x2'],w['y2']))
    dx,dy=x2-x1,y2-y1
    length=(dx*dx+dy*dy)**0.5
    t=float(w['thickness_m'])
    z=raised+int(w['storey_index'])*storey_h
    shape=Part.makeBox(length,t,storey_h)
    angle=math.degrees(math.atan2(dy,dx))
    shape.rotate(App.Vector(0,0,0),App.Vector(0,0,1),angle)
    shape.translate(App.Vector(x1,y1,z))
    obj=doc.addObject('Part::Feature',f'Wall_{idx+1}')
    obj.Label=w['wall_key']
    obj.Shape=shape

for idx,r in enumerate(layout['rooms']):
    z=raised+int(r['storey_index'])*storey_h+0.01
    room=doc.addObject('Part::Feature',f'Room_{idx+1}')
    room.Label=r['name']
    room.Shape=Part.makeBox(
        float(r['width']),float(r['depth']),0.03,
        App.Vector(float(r['x']),float(r['y']),z)
    )

roof_z=raised+int(layout['storeys'])*storey_h
roof=doc.addObject('Part::Feature','Roof_Concept')
ov=float(layout['roof']['eave_overhang_m'])
roof.Shape=Part.makeBox(
    float(layout['footprint']['width_m'])+2*ov,
    float(layout['footprint']['depth_m'])+2*ov,
    0.20,
    App.Vector(-ov,-ov,roof_z)
)

doc.recompute()
doc.saveAs(out_path)
print('PHOENIX_FREECAD_HANDOFF_OK',out_path)
"""


def _discover_freecad_python(freecadcmd_executable: str) -> Optional[str]:
    bindir = Path(freecadcmd_executable).resolve().parent
    for name in ("python.exe", "python3.exe", "python"):
        candidate = bindir / name
        if candidate.is_file():
            return str(candidate)
    return None


def _build_freecad_python_command(
    python_executable: str,
    script: Path,
    layout_json: Path,
    output_fcstd: Path,
) -> list[str]:
    return [str(python_executable), str(script), str(layout_json), str(output_fcstd)]


def _validate_result(
    cp: subprocess.CompletedProcess[str],
    output_fcstd: Path,
) -> tuple[bool, Dict[str, Any]]:
    marker_ok = "PHOENIX_FREECAD_HANDOFF_OK" in cp.stdout
    output_ok = output_fcstd.is_file() and output_fcstd.stat().st_size > 1000
    ev = {
        "exit_code": cp.returncode,
        "marker_ok": marker_ok,
        "output_ok": output_ok,
        "bytes": output_fcstd.stat().st_size if output_fcstd.is_file() else 0,
        "log_tail": cp.stdout[-3000:],
    }
    return cp.returncode == 0 and marker_ok and output_ok, ev


def _run_bundled_python(
    freecadcmd_executable: str,
    script: Path,
    layout_json: Path,
    output_fcstd: Path,
) -> Optional[Dict[str, Any]]:
    python_exe = _discover_freecad_python(freecadcmd_executable)
    if not python_exe:
        return None

    command = _build_freecad_python_command(python_exe, script, layout_json, output_fcstd)
    cp = subprocess.run(
        command,
        cwd=str(Path(freecadcmd_executable).resolve().parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    ok, ev = _validate_result(cp, output_fcstd)
    ev.update({
        "execution_mode": "BUNDLED_FREECAD_PYTHON",
        "python_executable": python_exe,
    })
    return {"ok": ok, "evidence": ev}


def _run_freecadcmd_fallback(
    freecadcmd_executable: str,
    script: Path,
    layout_json: Path,
    output_fcstd: Path,
) -> Dict[str, Any]:
    command = [
        str(freecadcmd_executable),
        str(script),
        "--pass",
        str(layout_json),
        str(output_fcstd),
    ]
    cp = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    ok, ev = _validate_result(cp, output_fcstd)
    ev.update({
        "execution_mode": "FREECADCMD_FALLBACK",
        "python_executable": None,
    })
    return {"ok": ok, "evidence": ev}


def run_freecad_handoff(
    layout_json: Path,
    output_fcstd: Path,
    executable: Optional[str] = None,
) -> Dict[str, Any]:
    exe = executable or discover_freecad()
    if not exe:
        return {"status": "NOT_FOUND", "executed": False, "output": None}

    output_fcstd.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="phoenix_freecad_") as td:
        script = Path(td) / "phoenix_freecad_handoff.py"
        script.write_text(_FREECAD_SCRIPT, encoding="utf-8")
        attempts = []

        primary = _run_bundled_python(exe, script, layout_json, output_fcstd)
        if primary is not None:
            attempts.append(primary["evidence"])
            if primary["ok"]:
                ev = primary["evidence"]
                return {
                    "status": "PASS",
                    "executed": True,
                    "executable": exe,
                    "execution_mode": ev["execution_mode"],
                    "python_executable": ev["python_executable"],
                    "output": str(output_fcstd),
                    "bytes": ev["bytes"],
                    "script_completion_marker": ev["marker_ok"],
                    "attempts": attempts,
                    "log_tail": ev["log_tail"],
                }

        if output_fcstd.exists():
            output_fcstd.unlink()

        fallback = _run_freecadcmd_fallback(exe, script, layout_json, output_fcstd)
        attempts.append(fallback["evidence"])
        if fallback["ok"]:
            ev = fallback["evidence"]
            return {
                "status": "PASS",
                "executed": True,
                "executable": exe,
                "execution_mode": ev["execution_mode"],
                "python_executable": None,
                "output": str(output_fcstd),
                "bytes": ev["bytes"],
                "script_completion_marker": ev["marker_ok"],
                "attempts": attempts,
                "log_tail": ev["log_tail"],
            }

    raise RuntimeError(f"FreeCAD handoff failed in all execution modes. Attempts={attempts}")
