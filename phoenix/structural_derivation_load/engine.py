#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re, unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

ENGINE_VERSION = "1.0.0"
PROJECT_ID = "PHX-RP-ANIJSTRAAT-616"
STATUS = "PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AND_LOAD_MODEL"
NEXT_STAGE = "PHOENIX_4.41_REAL_PROJECT_SOLVER_EXECUTION_AND_ELEMENT_VERIFICATION"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_text(path: Path) -> Tuple[str,int,Dict[str,Any]]:
    # pypdf is primary here because the prerequisite gap gate already performed
    # the detailed pdfplumber intake. This avoids a second expensive layout pass.
    errors=[]
    try:
        import pypdf
        r=pypdf.PdfReader(str(path))
        text="\n".join((p.extract_text() or "") for p in r.pages)
        return text,len(r.pages),{"backend":"pypdf","version":getattr(pypdf,"__version__","unknown"),"fallback":False}
    except Exception as e:
        errors.append(f"pypdf={e}")
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            text="\n".join((p.extract_text() or "") for p in pdf.pages)
            return text,len(pdf.pages),{"backend":"pdfplumber","version":getattr(pdfplumber,"__version__","unknown"),"fallback":True}
    except Exception as e:
        errors.append(f"pdfplumber={e}")
    raise RuntimeError("No PDF parser: "+" | ".join(errors))

def cumulative(vals: List[float]) -> List[float]:
    out=[0.0]
    for v in vals: out.append(round(out[-1]+float(v),6))
    return out

def qref(v: float, rho: float=1.225) -> float:
    return round(0.5*rho*v*v/1000.0,4)

def wall_line_weight(t: float,h: float,gamma: float)->float:
    return round(t*h*gamma,3)

def derive(pdf:Path,gap_json:Path,cfg:Dict[str,Any])->Dict[str,Any]:
    gap=json.loads(gap_json.read_text(encoding="utf-8"))
    if gap.get("status")!="PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AUTHORIZED":
        raise RuntimeError("Prerequisite gap gate not PASS")
    srcsha=sha256_file(pdf)
    if gap["source"]["sha256"]!=srcsha:
        raise RuntimeError("Prerequisite/source SHA mismatch")

    raw,pages,parser=extract_text(pdf)
    text=unicodedata.normalize("NFKC",raw)
    text=re.sub(r"\s+"," ",text)
    if pages<15: raise RuntimeError("Complete 15-page source not proven")

    patterns={
      "project":r"WOONHUIS\s*/?\s*ANIJSTRAAT\s*#?\s*616",
      "floor_plan":r"PLATTEGROND","foundation":r"FUNDERING","roof":r"KAPPLAN",
      "sections":r"DOORSNEDEN","details":r"DETAILS",
      "slab150":r"betonvloer\s*150\s*mm",
      "column200":r"kolom\s*:?\s*200\s*x\s*200",
      "strip":r"strook(?:fundering)?\s*800\s*x\s*200",
      "pad":r"schotel(?:fundering)?\s*1000\s*x\s*1000\s*x\s*200",
      "purlin":r"gording(?:en)?\s*:?\s*2[\"”]\s*x\s*3[\"”].*?900",
      "rafter":r"kapbeen\s*:?\s*2[\"”]\s*x\s*4[\"”]",
      "tie":r"trekbalk\s*:?\s*2[\"”]\s*x\s*4[\"”]"
    }
    evidence={k:bool(re.search(p,text,re.I)) for k,p in patterns.items()}
    missing=[k for k,v in evidence.items() if not v]
    if missing: raise RuntimeError("Source evidence missing: "+", ".join(missing))

    x=cumulative(cfg["geometry"]["x_grid_intervals_m"])
    y=cumulative(cfg["geometry"]["y_grid_intervals_m"])
    if abs(x[-1]-18.10)>1e-9 or abs(y[-1]-13.70)>1e-9:
        raise RuntimeError("Grid chain mismatch")

    geom={
      "source_status":"DERIVED_FROM_DRAWING_DIMENSION_CHAINS",
      "overall_outer_faces_m":{"x":18.20,"y":14.05},
      "structural_reference_grid_m":{
        "x_axis_labels":list("ABCDEFGHIJKLM"),"x_coordinates":x,
        "x_intervals":cfg["geometry"]["x_grid_intervals_m"],
        "y_axis_labels":[f"{i:02d}" for i in range(1,9)],"y_coordinates":y,
        "y_intervals":cfg["geometry"]["y_grid_intervals_m"]
      },
      "levels_m":{
        "finished_floor":0.0,"terrace_finished":-0.05,"ground_level":-0.20,
        "work_floor_underside":-0.97,"terrace_beam_underside":3.08,
        "structural_ring_beam_top":3.48,"roof_apex_or_rafter_top":6.73,
        "architectural_suspended_ceiling":2.70
      },
      "height_authority":"2.70 m interpreted as suspended finish ceiling; 3.48 m as structural wall/ring-beam height"
    }

    c=cfg["load_constants"]
    floor_parts=[
      ("rc_slab",0.150,c["concrete_density_kN_m3"]),
      ("screed",0.035,c["screed_density_kN_m3"]),
      ("tile",0.010,c["tile_density_kN_m3"]),
      ("adhesive",0.005,c["adhesive_density_kN_m3"])
    ]
    floor=[]
    for n,t,g in floor_parts:
        floor.append({"name":n,"thickness_m":t,"density_kN_m3":g,"gk_kN_m2":round(t*g,3)})
    floor_g=round(sum(v["gk_kN_m2"] for v in floor),3)

    h=3.48
    wall100=wall_line_weight(0.1,h,c["masonry_density_kN_m3"])
    wall150=wall_line_weight(0.15,h,c["masonry_density_kN_m3"])
    roof_g=round(c["roof_sheet_kN_m2"]+c["roof_timber_allowance_kN_m2"]+c["ceiling_allowance_kN_m2"]+c["roof_misc_allowance_kN_m2"],3)
    winds=[{
      "scenario":f"V{int(v)}","basic_velocity_m_s":float(v),
      "reference_dynamic_pressure_kN_m2":qref(float(v),c["air_density_kg_m3"]),
      "status":"SENSITIVITY_ONLY_NOT_A_SURINAME_NATIONAL_PARAMETER"
    } for v in cfg["wind_sensitivity"]["basic_velocity_scenarios_m_s"]]
    soils=[{
      "qa_kPa":float(qa),
      "existing_0p8m_strip_allowable_line_reaction_kN_m":round(float(qa)*0.8,2),
      "existing_1x1m_pad_allowable_reaction_kN":round(float(qa),2)
    } for qa in cfg["soil_sensitivity"]["allowable_bearing_kPa"]]

    tank_water=float(gap["tank"]["stored_water_weight_kN"])
    tank_env=round(tank_water*cfg["tank"]["preliminary_total_gravity_factor"],2)

    system={
      "primary_vertical_system":"MASONRY_WALLS_WITH_RC_RING_BEAMS_AND_LOCAL_RC_COLUMNS",
      "roof_system":"LIGHTWEIGHT_TIMBER_PITCHED_ROOF_WITH_TRAPEZOIDAL_SHEETING",
      "floor_system":"GROUND_BEARING_RC_SLAB",
      "foundation_system":"STRIP_FOOTINGS_UNDER_LOADBEARING_WALLS_PLUS_PAD_FOOTINGS_UNDER_COLUMNS",
      "tank_system":"ELEVATED_SEPARATE_SUPPORT_SYSTEM_REQUIRES_DEDICATED_LOAD_PATH",
      "load_path":[
        "roof -> timber roof members -> RC ring beams / candidate loadbearing masonry",
        "ring beams / masonry / RC columns -> strip/pad foundations -> soil",
        "ground-bearing floor slab -> fill/subgrade",
        "elevated tank -> dedicated support frame -> dedicated foundation"
      ],
      "wall_classification_rule":{
        "150mm":"PRELIMINARY_LOADBEARING_CANDIDATE",
        "100mm":"PRELIMINARY_PARTITION_OR_SECONDARY_WALL_UNLESS_LOAD_PATH_PROVES_OTHERWISE",
        "status":"REQUIRES_WALL_VECTOR_MAPPING_BEFORE_FINAL_ELEMENT_CHECK"
      }
    }

    load={
      "floor_on_ground":{
        "load_path":"DIRECT_TO_FILL_AND_SUBGRADE; NOT AUTOMATICALLY ADDED TO WALL FOOTING REACTIONS",
        "dead_load_components":floor,"gk_floor_build_up_kN_m2":floor_g,
        "residential_imposed_load_qk_kN_m2":cfg["loads"]["residential_floor_qk_kN_m2"]
      },
      "roof":{
        "roof_sheet_kN_m2":c["roof_sheet_kN_m2"],
        "timber_allowance_kN_m2":c["roof_timber_allowance_kN_m2"],
        "ceiling_allowance_kN_m2":c["ceiling_allowance_kN_m2"],
        "fixings_services_allowance_kN_m2":c["roof_misc_allowance_kN_m2"],
        "gk_total_kN_m2":roof_g,
        "nonaccessible_roof_imposed_qk_kN_m2":cfg["loads"]["roof_imposed_qk_kN_m2"]
      },
      "masonry":{"100mm_wall_line_weight_kN_m":wall100,"150mm_wall_line_weight_kN_m":wall150,"opening_reductions":"NOT_YET_APPLIED"},
      "rc_member_self_weight":{
        "ringbeam_100x150_kN_m":round(.1*.15*c["concrete_density_kN_m3"],3),
        "ringbeam_100x200_kN_m":round(.1*.2*c["concrete_density_kN_m3"],3),
        "terrace_beam_200x400_kN_m":round(.2*.4*c["concrete_density_kN_m3"],3),
        "column_200x200_per_3p48m_kN":round(.2*.2*h*c["concrete_density_kN_m3"],3)
      },
      "elevated_durotank":{
        "water_volume_m3":2.0,"known_water_weight_kN":tank_water,
        "preliminary_gravity_envelope_kN":tank_env,
        "envelope_factor":cfg["tank"]["preliminary_total_gravity_factor"],
        "note":"provisional allowance includes tank/support self-weight; exact support geometry not yet proven"
      },
      "wind_sensitivity":winds
    }

    authority=[
      {"id":"AUTH-RINGBEAM-001","source_conflict":["100x150 mm","100x200 mm"],"preliminary_model_choice":"100x200 mm primary reference; 100x150 retained as alternate","final_status":"UNRESOLVED_UNTIL_ELEMENT_VERIFICATION"},
      {"id":"AUTH-MASONRY-001","source_conflict":["4 inch","6 inch"],"preliminary_model_choice":"150 mm loadbearing candidate / 100 mm partition candidate","final_status":"UNRESOLVED_UNTIL_WALL_VECTOR_MAPPING"},
      {"id":"AUTH-HEIGHT-001","source_conflict":["2700 mm ceiling note","3430/3480 mm structural section"],"preliminary_model_choice":"2.70 m suspended ceiling / 3.48 m structural wall-ringbeam","final_status":"PRELIMINARY_RESOLUTION"}
    ]

    soil={"site_investigation":"NOT_AVAILABLE","preliminary_allowable_bearing_scenarios":soils,
          "groundwater_depth_scenarios_m_below_finished_floor":cfg["soil_sensitivity"]["groundwater_depth_scenarios_m"],
          "foundation_source_sizes":{"strip":"800 x 200 mm UNVERIFIED","pad":"1000 x 1000 x 200 mm UNVERIFIED"},
          "release_blocker":True}
    timber={"species":"UNKNOWN","actual_grade":"UNKNOWN","preliminary_strength_proxy":"EN 338 C18 proxy",
            "sensitivity_alternative":"C24 proxy",
            "source_members":{"purlin_nominal_mm":[50.8,76.2],"purlin_spacing_m":0.9,"rafter_nominal_mm":[50.8,101.6],"tie_nominal_mm":[50.8,101.6]},
            "warning":"nominal inch sizes do not prove dressed dimensions or graded species","release_blocker":True}
    code={"status":"ASSUMED_TECHNICAL_REFERENCE_NOT_PROVEN_SURINAME_LEGAL_BASIS",
          "references":["EN 1990","EN 1991","EN 1992","EN 1995","EN 1996","EN 1997"],
          "wind":{"methodology_reference":"EN 1991-1-4 concept","local_basic_wind_velocity":"NOT_PROVEN","implementation":"30/35/40 m/s sensitivity only"},
          "load_combinations":{"status":"PRELIMINARY_REFERENCE_ENVELOPES_ONLY","ULS_GRAVITY":"1.35G+1.50Q","ULS_WIND":"1.35G+1.50W+1.05Q","SLS_CHARACTERISTIC":"G+Q","SLS_WIND":"G+W+0.70Q"}}
    assumptions=[
      {"id":"ASM-CODE","value":"Eurocode family technical reference","confidence":"MEDIUM","release_blocker":True},
      {"id":"ASM-WIND","value":"30/35/40 m/s sensitivity only","confidence":"LOW","release_blocker":True},
      {"id":"ASM-SOIL","value":"qa 75/100/150 kPa sensitivity","confidence":"LOW","release_blocker":True},
      {"id":"ASM-GWT","value":"0.5/1.0/1.5 m depth sensitivity","confidence":"LOW","release_blocker":True},
      {"id":"ASM-TIMBER","value":"C18 proxy; C24 sensitivity","confidence":"LOW","release_blocker":True},
      {"id":"ASM-TANK","value":f"{tank_env:.2f} kN preliminary gravity envelope","confidence":"MEDIUM","release_blocker":True}
    ]

    return {
      "schema":"PHOENIX_STRUCTURAL_DERIVATION_LOAD_MODEL_1.0","engine_version":ENGINE_VERSION,
      "project_id":PROJECT_ID,"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source":{"pdf":pdf.name,"sha256":srcsha,"pages":pages,"parser":parser,"evidence":evidence},
      "prerequisite_gap_status":gap["status"],"geometry":geom,"structural_system":system,
      "authority_decisions":authority,"load_model":load,"soil_model":soil,"timber_model":timber,
      "code_basis":code,"assumptions":assumptions,
      "solver_seed":{"scope":"GLOBAL_ENVELOPE_GEOMETRY_ONLY","detailed_analysis_allowed":False,
        "files":["solver_seed/opensees_global_envelope.tcl","solver_seed/calculix_global_envelope.inp"],
        "next_required_action":"map actual wall/roof support vectors before solver execution"},
      "governance":{"existing_dimensions_are_verified":False,"preliminary_not_for_construction":True,
        "professional_structural_review_required":True,"for_construction_release":"LOCKED","solver_execution_in_this_stage":False},
      "status":STATUS,"next_stage":NEXT_STAGE
    }

def report(d):
    l=d["load_model"]
    lines=[
      "# PHOENIX 4.41 — Anijstraat #616 Structural Derivation + Load Model","",
      f"**Status:** `{d['status']}`","",
      "## Geometry",
      "- Outer envelope: **18.20 × 14.05 m**.",
      "- Structural grid chains: **18.10 × 13.70 m**.",
      "- Structural wall/ring-beam height: **3.48 m**.",
      "- Suspended architectural ceiling: **2.70 m**.","",
      "## Preliminary characteristic loads",
      f"- Ground-bearing floor build-up Gk: **{l['floor_on_ground']['gk_floor_build_up_kN_m2']:.2f} kN/m²**.",
      f"- Residential floor Qk reference: **{l['floor_on_ground']['residential_imposed_load_qk_kN_m2']:.2f} kN/m²**.",
      f"- Roof Gk allowance: **{l['roof']['gk_total_kN_m2']:.2f} kN/m²**.",
      f"- Roof Qk reference: **{l['roof']['nonaccessible_roof_imposed_qk_kN_m2']:.2f} kN/m²**.",
      f"- 100 mm wall line weight: **{l['masonry']['100mm_wall_line_weight_kN_m']:.2f} kN/m**.",
      f"- 150 mm wall line weight: **{l['masonry']['150mm_wall_line_weight_kN_m']:.2f} kN/m**.",
      f"- Tank known water weight: **{l['elevated_durotank']['known_water_weight_kN']:.2f} kN**.",
      f"- Tank preliminary gravity envelope: **{l['elevated_durotank']['preliminary_gravity_envelope_kN']:.2f} kN**.","",
      "## Governance",
      "- Wind is a sensitivity sweep, not a proven Suriname legal wind parameter.",
      "- Soil and timber assumptions remain release blockers.",
      "- Solver seeds are global-envelope pipeline models only.","",
      "**PRELIMINARY / NOT FOR CONSTRUCTION**","",
      f"Next stage: `{d['next_stage']}`"
    ]
    return "\n".join(lines)+"\n"

def opensees(d):
    x=d["geometry"]["structural_reference_grid_m"]["x_coordinates"][-1]
    y=d["geometry"]["structural_reference_grid_m"]["y_coordinates"][-1]
    z=d["geometry"]["levels_m"]["structural_ring_beam_top"]
    return f"""# GLOBAL ENVELOPE ONLY - NOT FOR CONSTRUCTION
# Source SHA256 {d['source']['sha256']}
wipe
model BasicBuilder -ndm 3 -ndf 6
node 1 0 0 0
node 2 {x} 0 0
node 3 {x} {y} 0
node 4 0 {y} 0
node 5 0 0 {z}
node 6 {x} 0 {z}
node 7 {x} {y} {z}
node 8 0 {y} {z}
fix 1 1 1 1 1 1 1
fix 2 1 1 1 1 1 1
fix 3 1 1 1 1 1 1
fix 4 1 1 1 1 1 1
set E 3.0e10
set G 1.25e10
geomTransf Linear 1 1 0 0
geomTransf Linear 2 0 0 1
element elasticBeamColumn 1 1 5 0.04 $E $G 2.25e-4 1.3333e-4 1.3333e-4 1
element elasticBeamColumn 2 2 6 0.04 $E $G 2.25e-4 1.3333e-4 1.3333e-4 1
element elasticBeamColumn 3 3 7 0.04 $E $G 2.25e-4 1.3333e-4 1.3333e-4 1
element elasticBeamColumn 4 4 8 0.04 $E $G 2.25e-4 1.3333e-4 1.3333e-4 1
element elasticBeamColumn 5 5 6 0.02 $E $G 2.82e-5 6.6667e-5 1.6667e-5 2
element elasticBeamColumn 6 6 7 0.02 $E $G 2.82e-5 6.6667e-5 1.6667e-5 2
element elasticBeamColumn 7 7 8 0.02 $E $G 2.82e-5 6.6667e-5 1.6667e-5 2
element elasticBeamColumn 8 8 5 0.02 $E $G 2.82e-5 6.6667e-5 1.6667e-5 2
# No design load pattern in this seed.
"""

def calculix(d):
    x=d["geometry"]["structural_reference_grid_m"]["x_coordinates"][-1]
    y=d["geometry"]["structural_reference_grid_m"]["y_coordinates"][-1]
    z=d["geometry"]["levels_m"]["structural_ring_beam_top"]
    return f"""** GLOBAL ENVELOPE ONLY - NOT FOR CONSTRUCTION
*NODE
1,0,0,0
2,{x},0,0
3,{x},{y},0
4,0,{y},0
5,0,0,{z}
6,{x},0,{z}
7,{x},{y},{z}
8,0,{y},{z}
*ELEMENT,TYPE=B31,ELSET=COLUMNS
1,1,5
2,2,6
3,3,7
4,4,8
*ELEMENT,TYPE=B31,ELSET=RING
5,5,6
6,6,7
7,7,8
8,8,5
*MATERIAL,NAME=CONCRETE_PRELIM
*ELASTIC
3.0E10,0.20
*DENSITY
2500.
*BEAM SECTION,ELSET=COLUMNS,MATERIAL=CONCRETE_PRELIM,SECTION=RECT
0.20,0.20
1.,0.,0.
*BEAM SECTION,ELSET=RING,MATERIAL=CONCRETE_PRELIM,SECTION=RECT
0.10,0.20
0.,0.,1.
*BOUNDARY
1,1,6
2,1,6
3,1,6
4,1,6
** No design load step in this seed.
"""

def write_outputs(d:Dict[str,Any],out:Path):
    out.mkdir(parents=True,exist_ok=True); (out/"solver_seed").mkdir(exist_ok=True)
    def dump(name,obj): (out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    dump("structural_derivation_load_model.json",d)
    for name,key in [("geometry_reference.json","geometry"),("structural_system.json","structural_system"),
                     ("load_model.json","load_model"),("soil_sensitivity.json","soil_model"),
                     ("timber_assumption.json","timber_model"),("code_basis.json","code_basis"),
                     ("authority_decisions.json","authority_decisions"),("assumptions_register.json","assumptions"),
                     ("solver_seed_manifest.json","solver_seed")]:
        dump(name,d[key])
    (out/"structural_derivation_load_report.md").write_text(report(d),encoding="utf-8")
    (out/"solver_seed/opensees_global_envelope.tcl").write_text(opensees(d),encoding="utf-8")
    (out/"solver_seed/calculix_global_envelope.inp").write_text(calculix(d),encoding="utf-8")
    manifest={}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="evidence_manifest.json":
            manifest[p.relative_to(out).as_posix()]={"sha256":sha256_file(p),"bytes":p.stat().st_size}
    dump("evidence_manifest.json",manifest)

def verify(path:Path):
    d=json.loads(path.read_text(encoding="utf-8"))
    assert d["status"]==STATUS
    assert d["source"]["pages"]>=15
    assert d["prerequisite_gap_status"]=="PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AUTHORIZED"
    assert d["load_model"]["floor_on_ground"]["gk_floor_build_up_kN_m2"]==4.77
    assert d["load_model"]["masonry"]["100mm_wall_line_weight_kN_m"]==6.96
    assert d["load_model"]["masonry"]["150mm_wall_line_weight_kN_m"]==10.44
    assert d["load_model"]["elevated_durotank"]["known_water_weight_kN"]==19.62
    assert d["governance"]["for_construction_release"]=="LOCKED"
    assert d["governance"]["solver_execution_in_this_stage"] is False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pdf",type=Path); ap.add_argument("--gap-json",type=Path)
    ap.add_argument("--config",type=Path); ap.add_argument("--output",type=Path)
    ap.add_argument("--verify-output",type=Path)
    a=ap.parse_args()
    if a.verify_output:
        verify(a.verify_output); print("PHOENIX_4_41_STRUCTURAL_DERIVATION_LOAD_OUTPUT_VERIFY=PASS"); return 0
    if not all([a.pdf,a.gap_json,a.config,a.output]): ap.error("required: --pdf --gap-json --config --output")
    d=derive(a.pdf,a.gap_json,json.loads(a.config.read_text(encoding="utf-8")))
    write_outputs(d,a.output)
    print(f"PROJECT_ID={PROJECT_ID}")
    print(f"PDF_BACKEND={d['source']['parser']['backend']}")
    print(f"PDF_PAGES={d['source']['pages']}")
    print(f"SOURCE_SHA256={d['source']['sha256']}")
    print(f"OUTER_ENVELOPE_M=18.2x14.05")
    print(f"STRUCTURAL_GRID_M=18.1x13.7")
    print(f"FLOOR_GK_KN_M2={d['load_model']['floor_on_ground']['gk_floor_build_up_kN_m2']}")
    print(f"ROOF_GK_KN_M2={d['load_model']['roof']['gk_total_kN_m2']}")
    print(f"WALL_100_KN_M={d['load_model']['masonry']['100mm_wall_line_weight_kN_m']}")
    print(f"WALL_150_KN_M={d['load_model']['masonry']['150mm_wall_line_weight_kN_m']}")
    print(f"TANK_PRELIM_ENVELOPE_KN={d['load_model']['elevated_durotank']['preliminary_gravity_envelope_kN']}")
    print("OPEN_SEES_SEED=PASS")
    print("CALCULIX_SEED=PASS")
    print("PRELIMINARY_NOT_FOR_CONSTRUCTION=TRUE")
    print("SOLVER_EXECUTION_IN_THIS_STAGE=FALSE")
    print(f"STRUCTURAL_DERIVATION_LOAD_STATUS={d['status']}")
    print(f"NEXT_STAGE={d['next_stage']}")
    print(f"OUTPUT={a.output}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
