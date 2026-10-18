"""AF-R3.4 evidence-bound candidate topology QA. NEVER approves architecture.

Derived spatial connectivity is diagnostic; the imported CAD-to-SketchUp registration
is not authenticated. No wall, opening or completeness inferences are authorized.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "phoenix.af_r3_4.candidate_topology.v1"
CANDIDATE = re.compile(r"^WALL_CANDIDATE_(\d{3})\b")

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def xykey(p, decimals=2):
    return (round(p[0], decimals), round(p[1], decimals))

def length_xy(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def point_segment_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx + dy*dy
    t = 0.0 if den < 1e-12 else max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)

def analyze(source, measurement, tolerance_mm=5.0):
    if not isinstance(tolerance_mm,(int,float)) or not math.isfinite(tolerance_mm) or not 0<tolerance_mm<=20:
        raise ValueError("unsafe tolerance")
    if measurement.get("schema") != "phoenix.af_r3_2.sketchup_measurement.v1" or measurement.get("units") != "mm":
        raise ValueError("unexpected measurement schema or units")
    if measurement.get("coordinate_system") != "sketchup_world_xyz_no_alignment_asserted":
        raise ValueError("unapproved coordinate system")
    if measurement.get("walls_verified") is not False or measurement.get("openings_verified") is not False or measurement.get("do_release") != "LOCKED":
        raise ValueError("unsafe upstream release claims")
    edges = measurement.get("edges")
    if not isinstance(edges,list) or measurement.get("edge_count") != len(edges):
        raise ValueError("measurement edge count mismatch")
    source_edges = source.get("components",{}).get("floorplan",{}).get("edges")
    if not isinstance(source_edges,list) or not source_edges:
        raise ValueError("R4 source floorplan missing")
    source_segments=[]
    for seg in source_edges:
        if not isinstance(seg,list) or len(seg)!=2 or any(len(v)!=3 or any(not isinstance(c,(float,int)) or not math.isfinite(c) for c in v) for v in seg):
            raise ValueError("invalid source segment")
        a,b=seg
        if abs(a[2])>0.001 or abs(b[2])>0.001:raise ValueError("nonflat source")
        source_segments.append((a,b))
    groups=defaultdict(lambda:{"top":[],"vertical":[],"other":[]})
    flat=0; orphan=0; seen=set()
    for e in edges:
        eid=e.get("id")
        if not isinstance(eid,str) or not eid or eid in seen:raise ValueError("duplicate/missing edge id")
        seen.add(eid)
        v=e.get("vertices_mm")
        if not isinstance(v,list) or len(v)!=2 or any(not isinstance(p,list) or len(p)!=3 or any(not isinstance(q,(int,float)) or not math.isfinite(q) for q in p) for p in v):
            raise ValueError("bad vertices")
        a,b=v
        if not isinstance(e.get("length_3d_mm"),(int,float)) or not math.isfinite(e["length_3d_mm"]) or abs(math.dist(a,b)-e["length_3d_mm"])>0.03:raise ValueError("invalid edge length")
        classification=e.get("classification")
        if classification=="UNKNOWN_FLAT_UNVERIFIED":
            if abs(a[2])>0.001 or abs(b[2])>0.001:raise ValueError("flat classified elevated")
            flat+=1;continue
        if classification!="MODEL_3D_GEOMETRY_UNVERIFIED":raise ValueError("unexpected classification")
        labels=set()
        for tag in e.get("source_tags",[]):
            match=CANDIDATE.match(tag)
            if match:labels.add(match.group(1))
        if len(labels)!=1:
            orphan+=1;continue
        group=groups[next(iter(labels))]
        if length_xy(a,b)<=0.001 and abs(a[2]-b[2])>0.001:group["vertical"].append((a,b))
        elif abs(a[2]-b[2])<=0.001 and a[2]>0.001:group["top"].append((a,b))
        else:group["other"].append((a,b))
    candidates=[]
    for key in sorted(groups):
        g=groups[key]; top=g["top"];vertical=g["vertical"]
        top_points={xykey(v) for ab in top for v in ab}
        vertical_points={xykey(ab[0]) for ab in vertical}
        matching_top=0
        for a,b in top:
            if any(max(point_segment_distance(a,c,d),point_segment_distance(b,c,d))<=tolerance_mm for c,d in source_segments):matching_top+=1
        # Edge-endpoint incidence only. No architectural wall junction inference.
        adjacency=defaultdict(int)
        for a,b in top:
            adjacency[xykey(a)]+=1;adjacency[xykey(b)]+=1
        candidates.append({"candidate_id":"WALL_CANDIDATE_"+key,
          "top_edges":len(top),"vertical_edges":len(vertical),"other_edges":len(g["other"]),
          "top_total_length_mm":round(sum(length_xy(a,b) for a,b in top),3),
          "top_edges_near_source":matching_top,
          "top_endpoints_without_vertical_xy":len(top_points-vertical_points),
          "open_top_endpoints":sum(1 for value in adjacency.values() if value==1),
          "z_top_values_mm":sorted({round(a[2],3) for a,b in top}),
          "classification":"GEOMETRIC_CANDIDATE_ONLY_UNVERIFIED",
          "wall_type":"UNKNOWN","wall_thickness_mm":None,
          "architectural_identity":"NOT_EVALUATED","openings":"NOT_EVALUATED"})
    return {"schema":SCHEMA,"status":"CANDIDATE_TOPOLOGY_MEASURED_ARCHITECTURE_UNVERIFIED",
      "input_counts":{"source_floorplan_edges":len(source_segments),"measured_edges":len(edges),"flat_edges":flat,"candidate_groups":len(candidates),"3d_without_single_candidate_tag":orphan},
      "candidate_totals":{"top_edges":sum(c['top_edges'] for c in candidates),"vertical_edges":sum(c['vertical_edges'] for c in candidates),"top_edges_near_source":sum(c['top_edges_near_source'] for c in candidates)},
      "candidates":candidates,"tolerance_mm":tolerance_mm,
      "gates":{"coordinate_alignment":"UNREGISTERED","external_wall_identity":"NOT_EVALUATED","internal_wall_identity":"NOT_EVALUATED","wall_thickness":"NOT_EVALUATED","junctions":"GEOMETRIC_ENDPOINTS_ONLY","door_and_window_openings":"NOT_EVALUATED","missing_wall_length":"NOT_EVALUATED","height_source_check":"NOT_EVALUATED","architectural_approval":"LOCKED","do_release":"LOCKED"}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--measurement',required=True);parser.add_argument('--output',required=True)
    a=parser.parse_args()
    try:
        source=json.loads(Path(a.source).read_text(encoding='utf-8'))
        measurement=json.loads(Path(a.measurement).read_text(encoding='utf-8'))
        report=analyze(source,measurement)
        report['sha256']={'source':digest(a.source),'measurement':digest(a.measurement)}
        code=0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        report={'schema':SCHEMA,'status':'BLOCKED','reason':str(exc),'do_release':'LOCKED'};code=2
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('PHOENIX_AF_R3_4_STATUS='+report['status']); print('REPORT='+a.output)
    return code
if __name__=='__main__':raise SystemExit(main())
