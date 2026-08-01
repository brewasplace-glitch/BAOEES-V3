from __future__ import annotations
import argparse,csv,hashlib,json,math,shutil
from pathlib import Path

def readj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def writej(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def csvw(p,fields,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise")
        w.writeheader();w.writerows(rows)

def dist(a,b):
    return math.hypot(float(b["x_m"])-float(a["x_m"]),float(b["y_m"])-float(a["y_m"]))

def wall_candidates(detail,profile):
    min_t=float(profile["assumptions"]["minimum_loadbearing_wall_thickness_m"])
    rows=[]
    for storey in detail.get("storeys",[]):
        for w in storey.get("walls",[]):
            t=float(w.get("thickness_m",0) or 0)
            category=w.get("category","")
            likely=(category=="external_wall" or t>=min_t)
            rows.append({
                "structural_id":"SW-"+w["element_id"],
                "architectural_element_id":w["element_id"],
                "storey_id":w["storey_id"],
                "candidate_type":"loadbearing_wall" if likely else "nonloadbearing_wall",
                "length_m":float(w.get("length_m",0) or 0),
                "height_m":float(w.get("height_m",0) or 0),
                "thickness_m":t,
                "material_hypothesis":profile["assumptions"]["default_wall_material"],
                "confidence":"HIGH" if category=="external_wall" else ("MEDIUM" if likely else "LOW"),
                "requires_review":True
            })
    return rows

def derive_axes(arch):
    xs=set();ys=set()
    for s in arch.get("storeys",[]):
        for r in s.get("spaces",[]):
            x=float(r.get("x_m",0));y=float(r.get("y_m",0))
            w=float(r.get("width_m",0));d=float(r.get("depth_m",0))
            xs.update([round(x,3),round(x+w,3)])
            ys.update([round(y,3),round(y+d,3)])
    axes=[]
    for i,x in enumerate(sorted(xs),1):
        axes.append({"axis_id":f"X{i:02d}","direction":"Y","coordinate_m":x})
    for i,y in enumerate(sorted(ys),1):
        axes.append({"axis_id":f"Y{i:02d}","direction":"X","coordinate_m":y})
    return axes

def column_candidates(arch,profile):
    target=float(profile["assumptions"]["column_grid_target_m"])
    rows=[]
    n=1
    for s in arch.get("storeys",[]):
        pts=set()
        for r in s.get("spaces",[]):
            x=float(r.get("x_m",0));y=float(r.get("y_m",0))
            w=float(r.get("width_m",0));d=float(r.get("depth_m",0))
            pts.update([(round(x,3),round(y,3)),(round(x+w,3),round(y,3)),(round(x,3),round(y+d,3)),(round(x+w,3),round(y+d,3))])
        for x,y in sorted(pts):
            rows.append({
                "structural_id":f"SC-{n:04d}",
                "storey_id":s["storey_id"],
                "x_m":x,"y_m":y,
                "material_hypothesis":profile["assumptions"]["default_column_material"],
                "grid_target_m":target,
                "confidence":"LOW",
                "requires_review":True
            });n+=1
    return rows

def slab_panels(arch,profile):
    rows=[]
    for s in arch.get("storeys",[]):
        for i,r in enumerate(s.get("spaces",[]),1):
            w=float(r.get("width_m",0));d=float(r.get("depth_m",0))
            span=min(w,d) if w and d else 0
            direction="X" if w<=d else "Y"
            rows.append({
                "panel_id":f"SLAB-{s['storey_id']}-{i:03d}",
                "storey_id":s["storey_id"],
                "architectural_space_id":r.get("space_id",""),
                "width_m":w,
                "depth_m":d,
                "candidate_span_m":span,
                "candidate_span_direction":direction,
                "material_hypothesis":profile["assumptions"]["default_slab_material"],
                "preferred_span_ok":span<=float(profile["assumptions"]["maximum_preferred_slab_span_m"]) if span else False,
                "requires_review":True
            })
    return rows

def beams_from_spaces(arch,profile):
    rows=[]
    n=1
    for s in arch.get("storeys",[]):
        for r in s.get("spaces",[]):
            x=float(r.get("x_m",0));y=float(r.get("y_m",0))
            w=float(r.get("width_m",0));d=float(r.get("depth_m",0))
            if w<=0 or d<=0: continue
            if w>=d:
                start={"x_m":x,"y_m":y+d/2};end={"x_m":x+w,"y_m":y+d/2}
            else:
                start={"x_m":x+w/2,"y_m":y};end={"x_m":x+w/2,"y_m":y+d}
            rows.append({
                "structural_id":f"SB-{n:04d}",
                "storey_id":s["storey_id"],
                "architectural_space_id":r.get("space_id",""),
                "start_x_m":round(start["x_m"],3),
                "start_y_m":round(start["y_m"],3),
                "end_x_m":round(end["x_m"],3),
                "end_y_m":round(end["y_m"],3),
                "candidate_span_m":round(dist(start,end),3),
                "material_hypothesis":profile["assumptions"]["default_beam_material"],
                "confidence":"LOW",
                "requires_review":True
            });n+=1
    return rows

def roof_supports(arch,profile):
    if not arch.get("storeys"): return []
    s=arch["storeys"][-1]
    rows=[]
    for i,r in enumerate(s.get("spaces",[]),1):
        rows.append({
            "roof_support_id":f"ROOF-{i:03d}",
            "storey_id":s["storey_id"],
            "architectural_space_id":r.get("space_id",""),
            "candidate_system":"primary_roof_member",
            "material_hypothesis":profile["assumptions"]["default_roof_material"],
            "requires_review":True
        })
    return rows

def stability_zones(walls):
    by_storey={}
    for w in walls:
        if w["candidate_type"]!="loadbearing_wall": continue
        by_storey.setdefault(w["storey_id"],[]).append(w["structural_id"])
    return [{
        "zone_id":f"STAB-{i:03d}",
        "storey_id":sid,
        "candidate_resisting_elements":"|".join(ids),
        "status":"CANDIDATE_ONLY",
        "requires_review":True
    } for i,(sid,ids) in enumerate(sorted(by_storey.items()),1)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-profile",required=True)
    ap.add_argument("--architectural-model",required=True)
    ap.add_argument("--detailed-elements",required=True)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    profile=readj(q.project_profile)
    arch=readj(q.architectural_model)
    detail=readj(q.detailed_elements)

    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("model","registers","reports","digital_twin"): (out/d).mkdir(parents=True,exist_ok=True)

    axes=derive_axes(arch)
    walls=wall_candidates(detail,profile)
    columns=column_candidates(arch,profile)
    slabs=slab_panels(arch,profile)
    beams=beams_from_spaces(arch,profile)
    roofs=roof_supports(arch,profile)
    stability=stability_zones(walls)

    model={
        "schema_version":"phoenix.structural-candidate-model/8.0.0",
        "project_id":profile.get("project_id",""),
        "candidate_only":True,
        "architectural_traceability":True,
        "axes":axes,
        "walls":walls,
        "columns":columns,
        "beams":beams,
        "slabs":slabs,
        "roof_supports":roofs,
        "stability_zones":stability,
        "release":{
            "professional_structural_review":False,
            "loads_complete":False,
            "analysis_complete":False,
            "member_design_complete":False,
            "structural_model_released":False
        }
    }
    writej(out/"model/structural_candidate_model.json",model)

    csvw(out/"registers/structural_axis_register.csv",
         ["axis_id","direction","coordinate_m"],axes)
    csvw(out/"registers/loadbearing_wall_candidate_register.csv",
         ["structural_id","architectural_element_id","storey_id","candidate_type","length_m","height_m","thickness_m","material_hypothesis","confidence","requires_review"],walls)
    csvw(out/"registers/column_candidate_register.csv",
         ["structural_id","storey_id","x_m","y_m","material_hypothesis","grid_target_m","confidence","requires_review"],columns)
    csvw(out/"registers/beam_candidate_register.csv",
         ["structural_id","storey_id","architectural_space_id","start_x_m","start_y_m","end_x_m","end_y_m","candidate_span_m","material_hypothesis","confidence","requires_review"],beams)
    csvw(out/"registers/slab_panel_register.csv",
         ["panel_id","storey_id","architectural_space_id","width_m","depth_m","candidate_span_m","candidate_span_direction","material_hypothesis","preferred_span_ok","requires_review"],slabs)
    csvw(out/"registers/roof_support_candidate_register.csv",
         ["roof_support_id","storey_id","architectural_space_id","candidate_system","material_hypothesis","requires_review"],roofs)
    csvw(out/"registers/stability_zone_register.csv",
         ["zone_id","storey_id","candidate_resisting_elements","status","requires_review"],stability)

    summary={
        "axis_count":len(axes),
        "wall_candidate_count":len(walls),
        "loadbearing_wall_candidate_count":sum(w["candidate_type"]=="loadbearing_wall" for w in walls),
        "column_candidate_count":len(columns),
        "beam_candidate_count":len(beams),
        "slab_panel_count":len(slabs),
        "roof_support_candidate_count":len(roofs),
        "stability_zone_count":len(stability),
        "candidate_model_only":True,
        "professional_structural_review_required":True
    }
    writej(out/"reports/structural_derivation_summary.json",summary)

    writej(out/"digital_twin/structural_candidate_model_v8_0_0.json",{
        "schema_version":"phoenix.digital-twin-structural-candidate/8.0.0",
        "project_id":profile.get("project_id",""),
        "source_architectural_model":str(Path(q.architectural_model)),
        "source_detailed_elements":str(Path(q.detailed_elements)),
        "traceability_enabled":True,
        "structural_candidate_model":"model/structural_candidate_model.json",
        "release":model["release"]
    })

    writej(out/"structural_derivation_release_gate.json",{
        "schema_version":"phoenix.structural-derivation-release-gate/8.0.0",
        "status":"LOCKED",
        "candidate_model_generated":True,
        "professional_structural_review":False,
        "loads_complete":False,
        "analysis_complete":False,
        "member_design_complete":False,
        "automatic_structural_approval":False,
        "structural_model_released":False
    })

    artifacts=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":
            artifacts.append({"path":p.relative_to(out).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha(p)})
    writej(out/"artifact_manifest.json",{"artifact_count":len(artifacts),"artifacts":artifacts})

    writej(out/"structural_derivation_engine_run.json",{
        "status":"PASSED",
        "project_id":profile.get("project_id",""),
        "pilot_project_dependency":False,
        "candidate_model_generated":True,
        "structural_model_released":False,
        "automatic_structural_approval":False
    })

    print("ARCHITECTURAL-TO-STRUCTURAL MODEL DERIVATION ENGINE: PASSED")
    print("STRUCTURAL AXES: GENERATED")
    print("LOADBEARING WALL CANDIDATES: GENERATED")
    print("COLUMN CANDIDATES: GENERATED")
    print("BEAM CANDIDATES: GENERATED")
    print("SLAB PANELS: GENERATED")
    print("ROOF SUPPORT CANDIDATES: GENERATED")
    print("STABILITY ZONES: GENERATED")
    print("ARCHITECTURAL TRACEABILITY: ENABLED")
    print("CENTRAL DIGITAL TWIN STRUCTURAL CANDIDATE WRITEBACK: PASSED")
    print("AUTOMATIC STRUCTURAL APPROVAL: DISABLED")
    print("STRUCTURAL MODEL RELEASE: LOCKED")

if __name__=="__main__":
    main()
