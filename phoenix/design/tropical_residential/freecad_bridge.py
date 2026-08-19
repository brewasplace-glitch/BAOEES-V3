from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .tool_discovery import discover_freecad


_FREECAD_SCRIPT = r"""
import json, sys
import FreeCAD as App
import Part

layout_path=sys.argv[-2]
out_path=sys.argv[-1]
layout=json.load(open(layout_path,'r',encoding='utf-8'))

doc=App.newDocument('PHOENIX_TROPICAL_RESIDENTIAL')
raised=float(layout['elevation']['raised_floor_m'])
storey_h=float(layout['storey_height_m'])

for s in range(int(layout['storeys'])):
    z=raised+s*storey_h-0.20
    slab=doc.addObject('Part::Feature',f'Slab_S{s+1}')
    slab.Shape=Part.makeBox(float(layout['footprint']['width_m']),float(layout['footprint']['depth_m']),0.20,App.Vector(0,0,z))

for idx,w in enumerate(layout['walls']):
    x1,y1,x2,y2=map(float,(w['x1'],w['y1'],w['x2'],w['y2']))
    dx,dy=x2-x1,y2-y1
    length=(dx*dx+dy*dy)**0.5
    t=float(w['thickness_m'])
    z=raised+int(w['storey_index'])*storey_h
    shape=Part.makeBox(length,t,storey_h)
    import math
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
    room.Shape=Part.makeBox(float(r['width']),float(r['depth']),0.03,App.Vector(float(r['x']),float(r['y']),z))

roof_z=raised+int(layout['storeys'])*storey_h
roof=doc.addObject('Part::Feature','Roof_Concept')
ov=float(layout['roof']['eave_overhang_m'])
roof.Shape=Part.makeBox(float(layout['footprint']['width_m'])+2*ov,float(layout['footprint']['depth_m'])+2*ov,0.20,App.Vector(-ov,-ov,roof_z))

doc.recompute()
doc.saveAs(out_path)
print('PHOENIX_FREECAD_HANDOFF_OK',out_path)
"""


def run_freecad_handoff(layout_json: Path, output_fcstd: Path, executable: Optional[str] = None) -> Dict[str, Any]:
    exe = executable or discover_freecad()
    if not exe:
        return {"status": "NOT_FOUND", "executed": False, "output": None}
    output_fcstd.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phoenix_freecad_") as td:
        script = Path(td) / "phoenix_freecad_handoff.py"
        script.write_text(_FREECAD_SCRIPT, encoding="utf-8")
        cp = subprocess.run(
            [exe, str(script), str(layout_json), str(output_fcstd)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120
        )
    ok = cp.returncode == 0 and output_fcstd.is_file() and output_fcstd.stat().st_size > 1000
    if not ok:
        raise RuntimeError(f"FreeCAD handoff failed ({cp.returncode}): {cp.stdout[-4000:]}")
    return {
        "status": "PASS", "executed": True, "executable": exe,
        "output": str(output_fcstd), "bytes": output_fcstd.stat().st_size,
        "log_tail": cp.stdout[-2000:]
    }
