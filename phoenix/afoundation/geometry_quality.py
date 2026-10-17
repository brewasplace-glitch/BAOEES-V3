"""AF-R3: conservative 2D source-to-model segment QA; no architecture certification.

Input coordinates are project-shared millimetres. Unsupported/missing evidence blocks.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'phoenix.af_r3.segment_qa.v1'


def read_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def check_segment(item):
    if not isinstance(item, (list, tuple)) or len(item) != 2:
        raise ValueError('Segment must be a pair of points')
    p, q = item
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for pt in (p,q) for v in pt):
        raise ValueError('Invalid or non-finite coordinate')
    if len(p) not in (2,3) or len(q) != len(p):
        raise ValueError('Point dimensionality mismatch')
    if len(p) == 3 and (abs(p[2]) > 0.001 or abs(q[2]) > 0.001):
        raise ValueError('Only planar XY segments accepted')
    x1,y1 = p[:2]; x2,y2 = q[:2]
    if math.hypot(x2-x1,y2-y1) < 0.001:
        raise ValueError('Zero-length segment')
    return ((float(x1),float(y1)), (float(x2),float(y2)))


def get_edges(d, role):
    if role == 'source' and d.get('components', {}).get('floorplan', {}).get('edges') is not None:
        return d['components']['floorplan']['edges']
    if d.get('schema') != SCHEMA or d.get('units') != 'mm' or d.get('coordinate_system') != 'source_world_xy':
        raise ValueError('Model/source schema, units or coordinate system invalid')
    if d.get('evidence_status') != 'MEASURED':
        raise ValueError('Only MEASURED geometry evidence accepted')
    return d['segments']


def segment_match(source, target, tolerance_mm, angle_deg):
    (a,b),(c,d) = source,target
    vx,vy=b[0]-a[0],b[1]-a[1]
    wx,wy=d[0]-c[0],d[1]-c[1]
    ln=math.hypot(vx,vy); lt=math.hypot(wx,wy)
    ux,uy=vx/ln,vy/ln
    alignment=abs((vx*wx+vy*wy)/(ln*lt))
    if alignment < math.cos(math.radians(angle_deg)):
        return 0.0
    # Require both endpoints of target lie on the source support line.
    if max(abs((c[0]-a[0])*uy-(c[1]-a[1])*ux),abs((d[0]-a[0])*uy-(d[1]-a[1])*ux)) > tolerance_mm:
        return 0.0
    tc=(c[0]-a[0])*ux+(c[1]-a[1])*uy
    td=(d[0]-a[0])*ux+(d[1]-a[1])*uy
    return max(0.0,min(ln,max(tc,td))-max(0.0,min(tc,td)))


def evaluate(source, model, tolerance_mm=20.0, angle_deg=2.0, baseline=None):
    if not 0 < tolerance_mm <= 500 or not 0 < angle_deg <= 15:
        raise ValueError('Unsafe tolerance')
    s=[check_segment(x) for x in get_edges(source,'source')]
    t=[check_segment(x) for x in get_edges(model,'model')]
    if not s or not t:
        raise ValueError('No measured source or model edges')
    # Merge overlapping projection intervals: a source segment may be matched by many fragments.
    matched=0.0
    for edge in s:
        (a,b)=edge
        length=math.dist(a,b)
        ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length
        intervals=[]
        for other in t:
            if segment_match(edge,other,tolerance_mm,angle_deg)>0:
                c,d=other
                lo=max(0.0,min((c[0]-a[0])*ux+(c[1]-a[1])*uy,(d[0]-a[0])*ux+(d[1]-a[1])*uy))
                hi=min(length,max((c[0]-a[0])*ux+(c[1]-a[1])*uy,(d[0]-a[0])*ux+(d[1]-a[1])*uy))
                if hi>lo: intervals.append((lo,hi))
        if intervals:
            intervals.sort()
            lo,hi=intervals[0]
            for l,h in intervals[1:]:
                if l<=hi:hi=max(hi,h)
                else:matched+=hi-lo;lo,hi=l,h
            matched+=hi-lo
    total=sum(math.dist(*e) for e in s)
    coverage=100*matched/total
    base_coverage=None if baseline is None else baseline.get('metrics',{}).get('source_edge_coverage_pct')
    if base_coverage is not None and (not isinstance(base_coverage,(int,float)) or not 0<=base_coverage<=100):
        raise ValueError('Invalid baseline coverage')
    regression = base_coverage is not None and coverage+1e-6 < base_coverage
    return {
       'schema':'phoenix.af_r3.qa_report.v1',
       'status':'REGRESSION_BLOCKED' if regression else 'GEOMETRY_EDGE_QA_PASS_UNVERIFIED_ARCHITECTURE',
       'evidence_scope':'2D source drawing edges only; NOT wall/roof/IFC certification',
       'metrics':{'source_edge_count':len(s),'model_edge_count':len(t),
                  'source_edge_length_mm':round(total,3),'matched_edge_length_mm':round(matched,3),
                  'source_edge_coverage_pct':round(coverage,4),
                  'baseline_coverage_pct':base_coverage,
                  'coverage_delta_pp':None if base_coverage is None else round(coverage-base_coverage,4)},
       'gates':{'regression': 'FAIL' if regression else ('NOT_EVALUATED' if baseline is None else 'PASS'),
                'architectural_wall_identity':'NOT_EVALUATED',
                'external_wall_coverage':'NOT_EVALUATED',
                'internal_wall_coverage':'NOT_EVALUATED',
                'wall_thickness':'NOT_EVALUATED',
                'openings':'NOT_EVALUATED',
                'model_3d_height':'NOT_EVALUATED',
                'do_release':'LOCKED'},
       'tolerance_mm':tolerance_mm,'angle_tolerance_deg':angle_deg,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True);ap.add_argument('--model',required=True)
    ap.add_argument('--output',required=True);ap.add_argument('--baseline')
    ap.add_argument('--tolerance-mm',type=float,default=20.0)
    args=ap.parse_args()
    out=Path(args.output)
    report={'schema':'phoenix.af_r3.qa_report.v1','status':'BLOCKED'}
    try:
        source=read_json(args.source);model=read_json(args.model)
        baseline=read_json(args.baseline) if args.baseline else None
        report=evaluate(source,model,args.tolerance_mm,baseline=baseline)
        report['inputs']={'source_sha256':sha256(args.source),'model_sha256':sha256(args.model),
                          'baseline_sha256':sha256(args.baseline) if args.baseline else None}
    except (ValueError,KeyError,TypeError,OSError, json.JSONDecodeError) as exc:
        report['reason']=f'{type(exc).__name__}: {exc}'
        report['gates']={'do_release':'LOCKED','architecture':'NOT_EVALUATED'}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PHOENIX_AF_R3_STATUS='+report['status'])
    print('REPORT='+str(out))
    return 0 if report['status']=='GEOMETRY_EDGE_QA_PASS_UNVERIFIED_ARCHITECTURE' else 2

if __name__=='__main__':
    raise SystemExit(main())
