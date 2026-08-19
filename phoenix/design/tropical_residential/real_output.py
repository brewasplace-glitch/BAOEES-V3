from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_storey_svg(path: Path, layout: Dict[str, Any], storey: int) -> None:
    fw=float(layout["footprint"]["width_m"])
    fd=float(layout["footprint"]["depth_m"])
    scale=min(900/max(fw,1.0),600/max(fd,1.0))
    ox,oy=80,100
    rooms=[r for r in layout["rooms"] if int(r["storey_index"])==storey]
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="800" viewBox="0 0 1100 800">',
        '<rect width="1100" height="800" fill="white"/>',
        f'<text x="40" y="42" font-family="Arial" font-size="26" font-weight="bold" fill="#1f4e78">PHOENIX Tropical Residential — Variant {html.escape(layout["variant_id"])} — Storey {storey+1}</text>',
        f'<text x="40" y="72" font-family="Arial" font-size="16" fill="#52606d">{html.escape(layout["strategy"])} | REAL SPATIAL CONCEPT LAYOUT | NOT FOR CONSTRUCTION</text>',
        f'<rect x="{ox}" y="{oy}" width="{fw*scale:.2f}" height="{fd*scale:.2f}" fill="#fbfdff" stroke="#102a43" stroke-width="5"/>'
    ]
    palette={"social":"#d9ead3","service":"#fff2cc","private":"#cfe2f3","circulation":"#eadcf8"}
    for r in rooms:
        x=ox+float(r["x"])*scale
        y=oy+(fd-(float(r["y"])+float(r["depth"])))*scale
        w=float(r["width"])*scale
        d=float(r["depth"])*scale
        fill=palette.get(str(r["zone"]),"#eeeeee")
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{d:.2f}" fill="{fill}" stroke="#1f4e78" stroke-width="2"/>')
        parts.append(f'<text x="{x+7:.2f}" y="{y+21:.2f}" font-family="Arial" font-size="14" fill="#102a43">{html.escape(r["name"])}</text>')
        parts.append(f'<text x="{x+7:.2f}" y="{y+39:.2f}" font-family="Arial" font-size="12" fill="#52606d">{float(r["area_m2"]):.1f} m²</text>')
    parts.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts),encoding="utf-8")


def write_layout_bundle(root: Path, layout: Dict[str, Any]) -> Dict[str, Any]:
    vdir=root/f"variant_{layout['variant_id']}"
    vdir.mkdir(parents=True,exist_ok=True)
    layout_json=vdir/"real_spatial_layout.json"
    write_json(layout_json,layout)
    svgs=[]
    for s in range(int(layout["storeys"])):
        p=vdir/f"storey_{s+1}_plan.svg"
        write_storey_svg(p,layout,s)
        svgs.append(str(p))
    return {"layout_json":str(layout_json),"svg_plans":svgs}
