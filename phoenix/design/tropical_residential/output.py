from __future__ import annotations
import json, html
from pathlib import Path

def _json(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")

def _svg(path, variant):
    label=html.escape(f"Variant {variant['variant_id']} - {variant['strategy']}")
    w=float(variant['width_m']); d=float(variant['depth_m'])
    scale=min(650/max(w,1),360/max(d,1)); bw=w*scale; bd=d*scale; x=(800-bw)/2; y=110
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="560" viewBox="0 0 800 560">
<rect width="800" height="560" fill="white"/>
<text x="30" y="42" font-family="Arial" font-size="24" font-weight="bold" fill="#1f4e78">Phoenix Tropical Residential</text>
<text x="30" y="72" font-family="Arial" font-size="18" fill="#334e68">{label}</text>
<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bd:.1f}" fill="#eaf4fb" stroke="#1f4e78" stroke-width="3"/>
<line x1="{x+bw/2:.1f}" y1="{y:.1f}" x2="{x+bw/2:.1f}" y2="{y+bd:.1f}" stroke="#1f4e78" stroke-width="2"/>
<line x1="{x:.1f}" y1="{y+bd/2:.1f}" x2="{x+bw:.1f}" y2="{y+bd/2:.1f}" stroke="#1f4e78" stroke-width="2"/>
<text x="30" y="505" font-family="Arial" font-size="15" fill="#8b1e1e">CONCEPT ONLY - NOT FOR CONSTRUCTION</text>
<text x="30" y="530" font-family="Arial" font-size="13" fill="#52606d">Schematic zoning. Exact room packing and IFC geometry follow in later authoring stages.</text>
</svg>'''
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(svg,encoding="utf-8")

def write_package(output_dir, project, variants, selected, stack, dt_patch, ifc_contract):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    summary={
      "engine":"PROJECT_PHOENIX_TROPICAL_RESIDENTIAL_DESIGN_ENGINE_FOUNDATION_v1_0",
      "project_id":project["project_id"],
      "variant_count":len(variants),
      "recommended_variant_id":selected["variant_id"],
      "recommended_strategy":selected["strategy"],
      "release_status":"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"
    }
    _json(out/'design_summary.json',summary); _json(out/'oss_capabilities.json',stack)
    _json(out/'digital_twin_patch.json',dt_patch); _json(out/'authoritative_ifc_contract.json',ifc_contract)
    for v in variants:
        _json(out/'variants'/f"variant_{v['variant_id']}.json",v); _svg(out/'variants'/f"variant_{v['variant_id']}.svg",v)
    return summary
