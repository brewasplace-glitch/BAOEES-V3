from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path

def area(poly):
    return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly))))/2

def validate(model):
    errors=[]
    levels={x["id"] for x in model["levels"]}
    walls={x["id"] for x in model["walls"]}
    for w in model["walls"]:
        if w["level_id"] not in levels: errors.append(f'{w["id"]}: missing level')
        if math.hypot(w["end"][0]-w["start"][0],w["end"][1]-w["start"][1])<=0: errors.append(f'{w["id"]}: zero length')
    for o in model["openings"]:
        if o["wall_id"] not in walls: errors.append(f'{o["id"]}: missing wall')
    for s in model["spaces"]:
        if s["level_id"] not in levels or area(s["polygon"])<=0: errors.append(f'{s["id"]}: invalid space')
    return errors

def bbl_checks(model):
    findings=[]
    for s in model["spaces"]:
        a=round(area(s["polygon"]),2)
        findings.append({"rule":"BBL-SPACE-AREA","subject":s["id"],"status":"PASS" if a>=5 else "REVIEW","observed":a,"required":5,"severity":"MEDIUM"})
        need=round(s.get("occupancy",0)*s.get("ventilation_lps_per_person",7),2)
        have=model.get("metadata",{}).get("ventilation_capacity_lps",{}).get(s["id"],0)
        findings.append({"rule":"BBL-VENTILATION","subject":s["id"],"status":"PASS" if have>=need else "FAIL","observed":have,"required":need,"severity":"HIGH"})
        findings.append({"rule":"BBL-ACCESSIBILITY","subject":s["id"],"status":"PASS" if s.get("accessible",False) else "REVIEW","observed":s.get("accessible",False),"required":True,"severity":"HIGH"})
    doors=[o for o in model["openings"] if o["kind"]=="door"]
    for d in doors:
        findings.append({"rule":"BBL-DOOR-WIDTH","subject":d["id"],"status":"PASS" if d["width_m"]>=0.85 else "FAIL","observed":d["width_m"],"required":0.85,"severity":"HIGH"})
    occ=sum(s.get("occupancy",0) for s in model["spaces"])
    req=2 if occ>60 else 1
    exits=sum(1 for d in doors if d["width_m"]>=0.85)
    findings.append({"rule":"BBL-ESCAPE-EXITS","subject":model["project_id"],"status":"PASS" if exits>=req else "FAIL","observed":exits,"required":req,"severity":"HIGH"})
    for st in model.get("stairs",[]):
        for rule,obs,reqv,ok in [
            ("BBL-STAIR-WIDTH",st["width_m"],1.1,st["width_m"]>=1.1),
            ("BBL-STAIR-RISE",st["rise_m"],0.188,st["rise_m"]<=0.188),
            ("BBL-STAIR-GOING",st["going_m"],0.22,st["going_m"]>=0.22),
            ("BBL-LEVEL-ACCESS",st.get("accessible_alternative",False),True,st.get("accessible_alternative",False))]:
            findings.append({"rule":rule,"subject":st["id"],"status":"PASS" if ok else "REVIEW","observed":obs,"required":reqv,"severity":"HIGH"})
    return findings

def floor_svg(model, level, path):
    walls=[w for w in model["walls"] if w["level_id"]==level["id"]]
    xs=[v for w in walls for v in (w["start"][0],w["end"][0])]; ys=[v for w in walls for v in (w["start"][1],w["end"][1])]
    scale=70; margin=70; minx,miny,maxx,maxy=min(xs),min(ys),max(xs),max(ys)
    width=int((maxx-minx)*scale+2*margin); height=int((maxy-miny)*scale+2*margin)
    px=lambda x:margin+(x-minx)*scale; py=lambda y:height-margin-(y-miny)*scale
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">','<rect width="100%" height="100%" fill="white"/>',
           f'<text x="30" y="35" font-family="Arial" font-size="22" font-weight="bold">{model["project_name"]} — {level["name"]}</text>']
    for w in walls:
        sw=max(3,w["thickness_m"]*scale)
        lines.append(f'<line x1="{px(w["start"][0]):.1f}" y1="{py(w["start"][1]):.1f}" x2="{px(w["end"][0]):.1f}" y2="{py(w["end"][1]):.1f}" stroke="black" stroke-width="{sw:.1f}"/>')
    for s in [x for x in model["spaces"] if x["level_id"]==level["id"]]:
        cx=sum(p[0] for p in s["polygon"])/len(s["polygon"]); cy=sum(p[1] for p in s["polygon"])/len(s["polygon"])
        lines.append(f'<text x="{px(cx):.1f}" y="{py(cy):.1f}" text-anchor="middle" font-family="Arial" font-size="15">{s["name"]} ({area(s["polygon"]):.1f} m²)</text>')
    lines.append(f'<text x="30" y="{height-20}" font-family="Arial" font-size="11">CONCEPT — professional review required</text></svg>')
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")

def elevation_svg(model,path):
    levels=sorted(model["levels"],key=lambda x:x["elevation_m"]); width=900;height=650
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">','<rect width="100%" height="100%" fill="white"/>',
           f'<text x="35" y="40" font-family="Arial" font-size="24" font-weight="bold">{model["project_name"]} — gevel</text>',
           '<rect x="130" y="140" width="640" height="410" fill="none" stroke="black" stroke-width="5"/>']
    for l in levels:
        y=550-l["elevation_m"]*85
        lines.append(f'<line x1="130" y1="{y}" x2="770" y2="{y}" stroke="#555" stroke-dasharray="8 6"/><text x="780" y="{y+5}" font-family="Arial" font-size="13">{l["name"]} {l["elevation_m"]:+.2f}</text>')
    lines.append('</svg>'); path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")

def section_svg(model,path):
    lines=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="650">','<rect width="100%" height="100%" fill="white"/>',
           f'<text x="35" y="40" font-family="Arial" font-size="24" font-weight="bold">{model["project_name"]} — doorsnede</text>']
    for l in sorted(model["levels"],key=lambda x:x["elevation_m"]):
        y=550-l["elevation_m"]*85
        lines.append(f'<line x1="130" y1="{y}" x2="770" y2="{y}" stroke="black" stroke-width="8"/><text x="780" y="{y+5}" font-family="Arial" font-size="13">{l["name"]}</text>')
    lines += ['<line x1="130" y1="550" x2="130" y2="150" stroke="black" stroke-width="8"/>','<line x1="770" y1="550" x2="770" y2="150" stroke="black" stroke-width="8"/>','</svg>']
    path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")

def run(model_path, output_dir):
    model=json.loads(Path(model_path).read_text(encoding="utf-8"))
    errors=validate(model)
    if errors: raise ValueError("; ".join(errors))
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    (out/"01_canonical_architectural_model.json").write_text(json.dumps(model,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    findings=bbl_checks(model); summary={k:sum(x["status"]==k for x in findings) for k in ("PASS","FAIL","REVIEW")}
    (out/"02_bbl_findings.json").write_text(json.dumps({"summary":summary,"findings":findings},indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    with (out/"03_bbl_findings.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["rule","subject","status","observed","required","severity"],lineterminator="\n");w.writeheader();w.writerows(findings)
    drawings=out/"drawings"; drawings.mkdir(exist_ok=True)
    for l in model["levels"]: floor_svg(model,l,drawings/f'floor_plan_{l["id"]}.svg')
    elevation_svg(model,drawings/"elevation_concept.svg"); section_svg(model,drawings/"section_concept.svg")
    with (out/"space_schedule.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["id","level","name","function","area_m2","occupancy","accessible"])
        for s in sorted(model["spaces"],key=lambda x:x["id"]): w.writerow([s["id"],s["level_id"],s["name"],s["function"],f'{area(s["polygon"]):.2f}',s.get("occupancy",0),s.get("accessible",False)])
    html=f"""<!doctype html><meta charset='utf-8'><title>{model["project_name"]}</title><body style='font-family:Arial;margin:40px'><h1>{model["project_name"]}</h1><h2>Integrated Architectural, Bbl and Drawing Suite v4.0.0</h2><p>Levels: {len(model["levels"])} | Spaces: {len(model["spaces"])} | Walls: {len(model["walls"])}</p><p>BBL PASS: {summary["PASS"]} | FAIL: {summary["FAIL"]} | REVIEW: {summary["REVIEW"]}</p><p><b>Release: CONCEPT ONLY — professional validation required.</b></p></body>"""
    (out/"04_integrated_report.html").write_text(html,encoding="utf-8",newline="\n")
    artifacts=[]
    for p in sorted(x for x in out.rglob("*") if x.is_file()):
        artifacts.append({"path":p.relative_to(out).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size_bytes":p.stat().st_size})
    manifest={"schema_version":"phoenix.architectural-suite-output/4.0.0","project_id":model["project_id"],"release_status":"CONCEPT_REVIEW_REQUIRED","summary":summary,"artifacts":artifacts}
    (out/"05_artifact_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    return manifest
