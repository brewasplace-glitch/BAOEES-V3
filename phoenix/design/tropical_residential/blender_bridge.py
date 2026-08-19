from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .tool_discovery import discover_blender


_BLENDER_SCRIPT = r"""
import bpy, json, math, sys
from mathutils import Vector

argv=sys.argv
sep=argv.index('--')
layout_path=argv[sep+1]
out_path=argv[sep+2]
layout=json.load(open(layout_path,'r',encoding='utf-8'))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1.0

def cube(name, x, y, z, sx, sy, sz, angle=0.0):
    bpy.ops.mesh.primitive_cube_add(location=(x+sx/2,y+sy/2,z+sz/2),rotation=(0,0,math.radians(angle)))
    o=bpy.context.object
    o.name=name
    o.dimensions=(sx,sy,sz)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return o

raised=float(layout['elevation']['raised_floor_m'])
storey_h=float(layout['storey_height_m'])
fw=float(layout['footprint']['width_m'])
fd=float(layout['footprint']['depth_m'])

for s in range(int(layout['storeys'])):
    cube(f'Slab_S{s+1}',0,0,raised+s*storey_h-0.20,fw,fd,0.20)

for i,w in enumerate(layout['walls']):
    x1,y1,x2,y2=map(float,(w['x1'],w['y1'],w['x2'],w['y2']))
    dx,dy=x2-x1,y2-y1
    length=(dx*dx+dy*dy)**0.5
    angle=math.degrees(math.atan2(dy,dx))
    t=float(w['thickness_m'])
    z=raised+int(w['storey_index'])*storey_h
    # local box is rotated around its centre; place centre on wall segment.
    bpy.ops.mesh.primitive_cube_add(location=((x1+x2)/2,(y1+y2)/2,z+storey_h/2),rotation=(0,0,math.radians(angle)))
    o=bpy.context.object
    o.name=f'Wall_{i+1}'
    o.dimensions=(length,t,storey_h)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

ov=float(layout['roof']['eave_overhang_m'])
cube('Roof_Concept',-ov,-ov,raised+int(layout['storeys'])*storey_h,fw+2*ov,fd+2*ov,0.20)

scene['PHOENIX_PROJECT_ID']=layout['project_id']
scene['PHOENIX_VARIANT_ID']=layout['variant_id']
scene['PHOENIX_RELEASE_STATUS']='CONCEPT_ONLY_NOT_FOR_CONSTRUCTION'
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print('PHOENIX_BLENDER_HANDOFF_OK',out_path)
"""


def run_blender_handoff(layout_json: Path, output_blend: Path, executable: Optional[str] = None) -> Dict[str, Any]:
    exe = executable or discover_blender()
    if not exe:
        return {"status": "NOT_FOUND", "executed": False, "output": None}
    output_blend.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phoenix_blender_") as td:
        script = Path(td) / "phoenix_blender_handoff.py"
        script.write_text(_BLENDER_SCRIPT, encoding="utf-8")
        cp = subprocess.run(
            [exe, "--background", "--python", str(script), "--", str(layout_json), str(output_blend)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180
        )
    ok = cp.returncode == 0 and output_blend.is_file() and output_blend.stat().st_size > 1000
    if not ok:
        raise RuntimeError(f"Blender handoff failed ({cp.returncode}): {cp.stdout[-4000:]}")
    return {
        "status": "PASS", "executed": True, "executable": exe,
        "output": str(output_blend), "bytes": output_blend.stat().st_size,
        "log_tail": cp.stdout[-2000:]
    }
