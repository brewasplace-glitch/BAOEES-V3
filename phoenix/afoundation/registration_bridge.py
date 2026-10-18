"""AF-R3.3: conservative 3D candidate-to-2D source line QA; no alignment or wall approval."""
import argparse, hashlib, json, math
from pathlib import Path

SCHEMA='phoenix.af_r3_3.registration_review.v1'

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def evaluate(source,measure, tolerance=5.0):
 if not 0<tolerance<=20: raise ValueError('unsafe tolerance')
 if source.get('components',{}).get('floorplan',{}).get('edges') is None:raise ValueError('R4 floorplan missing')
 if measure.get('schema')!='phoenix.af_r3_2.sketchup_measurement.v1' or measure.get('units')!='mm':raise ValueError('measurement schema/units invalid')
 if measure.get('coordinate_system')!='sketchup_world_xyz_no_alignment_asserted':raise ValueError('unrecognized coordinates')
 if measure.get('walls_verified') is not False or measure.get('do_release')!='LOCKED':raise ValueError('invalid approval claim')
 if measure.get('edge_count')!=len(measure.get('edges',[])):raise ValueError('edge count mismatch')
 src=source['components']['floorplan']['edges']
 source_set=set()
 for a,b in src:
  if abs(a[2])>0.001 or abs(b[2])>0.001:raise ValueError('nonplanar source')
  source_set.add(tuple(sorted(((round(a[0],3),round(a[1],3)),(round(b[0],3),round(b[1],3))))))
 ztop=0; vertical=0; flat=0; invalid=0; projected=[]; zs=[]; ids=set(); tags=set()
 for e in measure['edges']:
  uid=e.get('id');v=e.get('vertices_mm'); cat=e.get('classification');
  if uid in ids or not uid:raise ValueError('invalid edge id')
  ids.add(uid)
  if not isinstance(v,list) or len(v)!=2 or any(len(p)!=3 or any(not isinstance(q,(int,float)) or not math.isfinite(q) for q in p) for p in v):raise ValueError('invalid vertices')
  a,b=v; length=math.dist(a,b)
  if abs(length-e.get('length_3d_mm',-1))>0.02:raise ValueError('length mismatch')
  if cat=='UNKNOWN_FLAT_UNVERIFIED':flat+=1;continue
  if cat!='MODEL_3D_GEOMETRY_UNVERIFIED':invalid+=1;continue
  if abs(a[0]-b[0])<=0.001 and abs(a[1]-b[1])<=0.001 and abs(a[2]-b[2])>0.001:vertical+=1;zs.append(max(a[2],b[2]));continue
  if a[2]>0.001 and abs(a[2]-b[2])<=0.001:
   ztop+=1;zs.append(a[2]);projected.append((a[:2],b[:2]));tags.update(s for s in e.get('source_tags',[]) if 'WALL_CANDIDATE_' in s);continue
  invalid+=1
 # Independent geometric test: XY endpoint agreement, descriptive only, never registered alignment.
 def point_dist_to_seg(p,a,b):
  vx=b[0]-a[0];vy=b[1]-a[1];d=vx*vx+vy*vy
  if d<1e-9:return math.dist(p,a)
  t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/d))
  return math.dist(p,(a[0]+t*vx,a[1]+t*vy))
 # only count a match when both target endpoints are close to one source segment
 matched=0
 for a,b in projected:
  for c,d in src:
   if max(point_dist_to_seg(a,c[:2],d[:2]),point_dist_to_seg(b,c[:2],d[:2]))<=tolerance:
    matched+=1;break
 return {'schema':SCHEMA,'status':'GEOMETRIC_CANDIDATES_MEASURED_REGISTRATION_UNVERIFIED',
 'counts':{'r4_floorplan_edges':len(src),'measurement_edges':len(ids),'flat_unverified':flat,'top_edges_3d':ztop,'vertical_edges_3d':vertical,'other_3d_edges':invalid,'top_edges_with_source_xy_proximity':matched,'candidate_tags':len(tags)},
 'height_mm':{'min':min(zs) if zs else None,'max':max(zs) if zs else None},
 'gates':{'source_to_model_coordinate_alignment':'NOT_EVALUATED','geometric_2d_proximity':'DESCRIPTIVE_ONLY','architectural_wall_identity':'NOT_EVALUATED','outside_wall_coverage':'NOT_EVALUATED','inside_wall_coverage':'NOT_EVALUATED','openings':'NOT_EVALUATED','do_release':'LOCKED'},
 'tolerance_mm':tolerance}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--measurement',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 try:
  s=json.load(open(a.source,encoding='utf8'));m=json.load(open(a.measurement,encoding='utf8'));r=evaluate(s,m);r['sha256']={'source':digest(a.source),'measurement':digest(a.measurement)};code=0
 except (ValueError,KeyError,TypeError,OSError) as ex:r={'schema':SCHEMA,'status':'BLOCKED','error':str(ex),'do_release':'LOCKED'};code=2
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,indent=2),encoding='utf8');print('PHOENIX_AF_R3_3_STATUS='+r['status']);print('REPORT='+a.output);return code
if __name__=='__main__':raise SystemExit(main())
