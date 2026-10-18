"""AF-R3.5: source-bound line attribution, never wall recognition/approval.

R4 CAD review is an unclassified collection of flat segments, NOT a wall schedule.
Per-candidate matching requires BOTH endpoints of the same top edge near one R4
segment and a collinear direction; ambiguous associations stay ambiguous.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA='phoenix.af_r3_5.source_bound_walls.v1'
TAG=re.compile(r'^WALL_CANDIDATE_(\d{3})\b')

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def validate_point(p):
    if not isinstance(p,(list,tuple)) or len(p)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in p):
        raise ValueError('invalid 3D point')

def dist_point_segment(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    t=0 if den<1e-12 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def source_alignment(a,b,c,d,tol,angle_deg):
    u=(b[0]-a[0],b[1]-a[1]);v=(d[0]-c[0],d[1]-c[1]);lu=math.hypot(*u);lv=math.hypot(*v)
    if lu<=0.01 or lv<=0.01:return False
    cos=abs((u[0]*v[0]+u[1]*v[1])/(lu*lv))
    if cos < math.cos(math.radians(angle_deg))-1e-12:return False
    return max(dist_point_segment(a,c,d),dist_point_segment(b,c,d)) <= tol

def analyze(source,measurement,tolerance_mm=5.,angular_tolerance_deg=1.):
    if (isinstance(tolerance_mm,bool) or not isinstance(tolerance_mm,(int,float)) or
        not math.isfinite(tolerance_mm) or not 0<tolerance_mm<=20):raise ValueError('unsafe metric tolerance')
    if (isinstance(angular_tolerance_deg,bool) or not isinstance(angular_tolerance_deg,(int,float)) or
        not math.isfinite(angular_tolerance_deg) or not 0<angular_tolerance_deg<=5):raise ValueError('unsafe angular tolerance')
    if measurement.get('schema')!='phoenix.af_r3_2.sketchup_measurement.v1' or measurement.get('units')!='mm':raise ValueError('wrong measurement schema/units')
    if measurement.get('coordinate_system')!='sketchup_world_xyz_no_alignment_asserted':raise ValueError('unexpected frame')
    if measurement.get('walls_verified') is not False or measurement.get('openings_verified') is not False or measurement.get('do_release')!='LOCKED':raise ValueError('unsafe upstream claims')
    if measurement.get('model_modified') is not False:raise ValueError('source model modified or unconfirmed')
    src=source.get('components',{}).get('floorplan',{}).get('edges')
    if not isinstance(src,list) or not src:raise ValueError('missing R4 floorplan')
    source_lines=[]
    for i,e in enumerate(src):
        if not isinstance(e,list) or len(e)!=2:raise ValueError('invalid R4 edge')
        a,b=e;validate_point(a);validate_point(b)
        if abs(a[2])>0.001 or abs(b[2])>0.001:raise ValueError('nonflat source')
        if math.dist(a,b)<=.01:raise ValueError('degenerate source segment')
        source_lines.append((a,b))
    edges=measurement.get('edges')
    if not isinstance(edges,list) or measurement.get('edge_count')!=len(edges):raise ValueError('edge count mismatch')
    seen=set();groups=defaultdict(list);flat=0;vertical=0;unassigned=0
    for e in edges:
        eid=e.get('id');pts=e.get('vertices_mm')
        if not isinstance(eid,str) or not eid or eid in seen:raise ValueError('duplicate/missing edge ID')
        seen.add(eid)
        if not isinstance(pts,list) or len(pts)!=2:raise ValueError('invalid measured edge')
        a,b=pts;validate_point(a);validate_point(b)
        L=e.get('length_3d_mm')
        if isinstance(L,bool) or not isinstance(L,(int,float)) or not math.isfinite(L) or abs(math.dist(a,b)-L)>.03:raise ValueError('edge length mismatch')
        cls=e.get('classification')
        if cls=='UNKNOWN_FLAT_UNVERIFIED':
            if max(abs(a[2]),abs(b[2]))>.001:raise ValueError('non-flat flat-classified edge')
            flat+=1;continue
        if cls!='MODEL_3D_GEOMETRY_UNVERIFIED':raise ValueError('unexpected edge classification')
        tags=e.get('source_tags')
        if not isinstance(tags,list):raise ValueError('tags unavailable')
        labels={m.group(1) for t in tags if isinstance(t,str) for m in [TAG.match(t)] if m}
        if len(labels)!=1:unassigned+=1;continue
        label='WALL_CANDIDATE_'+next(iter(labels))
        xy=math.hypot(a[0]-b[0],a[1]-b[1])
        if xy<.001 and abs(a[2]-b[2])>.001:vertical+=1;continue
        if abs(a[2]-b[2])>.001 or a[2]<=.001:raise ValueError('unrecognized elevated geometry')
        groups[label].append((eid,a,b))
    candidates=[];matched_set=set();referenced=Counter()
    for label in sorted(groups):
        detail=[];unmatched=0;ambiguous=0;uniques=0
        for eid,a,b in groups[label]:
            matches=[i for i,(c,d) in enumerate(source_lines) if source_alignment(a,b,c,d,tolerance_mm,angular_tolerance_deg)]
            status='NONE' if not matches else 'ONE' if len(matches)==1 else 'AMBIGUOUS'
            unmatched+=(not matches);ambiguous+=(len(matches)>1);uniques+=(len(matches)==1)
            referenced.update(matches);matched_set.update(matches)
            detail.append({'edge_id':eid,'length_mm':round(math.dist(a,b),3),'source_segment_indices':matches,'match_status':status})
        candidates.append({'candidate_id':label,'top_edges':len(detail),'unique_source_match_edges':uniques,
            'ambiguous_source_match_edges':ambiguous,'unmatched_top_edges':unmatched,
            'source_evidence':detail,'wall_identity':'NOT_EVALUATED','wall_type':'UNKNOWN',
            'missing_wall_length_mm':None,'openings':'NOT_EVALUATED'})
    total_top=sum(c['top_edges'] for c in candidates)
    return {'schema':SCHEMA,'status':'SOURCE_LINE_ATTRIBUTION_DESCRIPTIVE_ONLY',
       'input_counts':{'r4_floorplan_edges':len(source_lines),'r12_measured_edges':len(edges),
          'r12_flat_edges':flat,'r12_vertical_edges':vertical,'r12_unassigned_3d_edges':unassigned,
          'candidate_groups':len(candidates),'top_edges':total_top},
       'source_attribution':{'top_edges_one_match':sum(c['unique_source_match_edges'] for c in candidates),
          'top_edges_ambiguous':sum(c['ambiguous_source_match_edges'] for c in candidates),
          'top_edges_no_match':sum(c['unmatched_top_edges'] for c in candidates),
          'distinct_r4_segments_referenced':len(matched_set),
          'r4_segments_not_referenced':len(source_lines)-len(matched_set),
          'caution':'Unreferenced R4 lines are not proven missing walls; R4 contains unclassified linework'},
       'candidates':candidates,
       'tolerance_mm':tolerance_mm,'angular_tolerance_deg':angular_tolerance_deg,
       'gates':{'coordinate_registration':'UNVERIFIED',
          'source_line_to_wall_classification':'NOT_EVALUATED',
          'outside_wall_coverage':'NOT_EVALUATED',
          'inside_wall_coverage':'NOT_EVALUATED',
          'missing_wall_length':'NOT_EVALUATED',
          'wall_thickness':'NOT_EVALUATED','openings':'NOT_EVALUATED',
          'architectural_approval':'LOCKED','do_release':'LOCKED'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--measurement',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    try:
        report=analyze(json.loads(Path(a.source).read_text(encoding='utf-8')),
                       json.loads(Path(a.measurement).read_text(encoding='utf-8')))
        report['sha256']={'source':sha256(a.source),'measurement':sha256(a.measurement)}
        rc=0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        report={'schema':SCHEMA,'status':'BLOCKED','reason':str(exc),'gates':{'do_release':'LOCKED'}};rc=2
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PHOENIX_AF_R3_5_STATUS='+report['status']);print('REPORT='+a.output)
    return rc
if __name__=='__main__':raise SystemExit(main())
