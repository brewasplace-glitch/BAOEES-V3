"""AF-R3.6: read-only, conservative R4 source ambiguity decomposition.

A geometric duplicate is NOT independent documentary evidence. No wall identity,
missing-wall length, approved registration, or construction release is asserted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'phoenix.af_r3_6.source_evidence_disambiguation.v1'
UPSTREAM = 'phoenix.af_r3_5.source_bound_walls.v1'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def valid_point(p):
    return isinstance(p, list) and len(p) == 3 and all(type(v) in (float, int) and math.isfinite(v) for v in p)

def key_segment(e, precision_mm=0.01):
    if not isinstance(e,list) or len(e)!=2 or not all(valid_point(p) for p in e):
        raise ValueError('invalid R4 geometry')
    if abs(e[0][2])>.001 or abs(e[1][2])>.001:
        raise ValueError('nonflat R4 geometry')
    if math.dist(e[0],e[1])<.01:
        raise ValueError('degenerate R4 geometry')
    ends = [tuple(int(round(p[k]/precision_mm)) for k in (0,1)) for p in e]
    return tuple(sorted(ends))

def analyze(source, prior):
    if prior.get('schema') != UPSTREAM or prior.get('status') != 'SOURCE_LINE_ATTRIBUTION_DESCRIPTIVE_ONLY':
        raise ValueError('unexpected upstream schema/status')
    gates=prior.get('gates',{})
    if gates.get('coordinate_registration')!='UNVERIFIED' or gates.get('do_release')!='LOCKED' or gates.get('architectural_approval')!='LOCKED':
        raise ValueError('unsafe upstream release state')
    for field in ('outside_wall_coverage','inside_wall_coverage','missing_wall_length','source_line_to_wall_classification'):
        if gates.get(field)!='NOT_EVALUATED': raise ValueError('unsafe upstream claims')
    src=source.get('components',{}).get('floorplan',{}).get('edges')
    if not isinstance(src,list) or len(src)!=prior.get('input_counts',{}).get('r4_floorplan_edges'):
        raise ValueError('R4 input count mismatch')
    by_geo={}
    for i,e in enumerate(src):
        by_geo.setdefault(key_segment(e),[]).append(i)
    keys={i:key_segment(e) for i,e in enumerate(src)}
    candidates=prior.get('candidates')
    if not isinstance(candidates,list) or len(candidates)!=prior.get('input_counts',{}).get('candidate_groups'):
        raise ValueError('candidate count mismatch')
    output=[]; seen=set(); seen_edges=set(); total=0; ambiguous=0; one=0; no=0
    equivalent=0; competing=0
    for c in candidates:
        cid=c.get('candidate_id')
        if not isinstance(cid,str) or cid in seen:raise ValueError('duplicate candidate ID')
        seen.add(cid)
        items=c.get('source_evidence')
        if not isinstance(items,list) or len(items)!=c.get('top_edges'):raise ValueError('invalid source evidence')
        if c.get('wall_identity')!='NOT_EVALUATED' or c.get('wall_type')!='UNKNOWN' or c.get('missing_wall_length_mm') is not None or c.get('openings')!='NOT_EVALUATED':
            raise ValueError('unsafe candidate claims')
        rows=[]; local_one=local_amb=local_none=0
        for item in items:
            eid=item.get('edge_id'); inds=item.get('source_segment_indices'); status=item.get('match_status')
            if not isinstance(eid,str) or not eid or eid in seen_edges:raise ValueError('duplicate edge ID')
            seen_edges.add(eid)
            if not isinstance(inds,list) or len(set(inds))!=len(inds) or any(type(i)!=int or not 0<=i<len(src) for i in inds):
                raise ValueError('invalid source indices')
            expected='NONE' if not inds else 'ONE' if len(inds)==1 else 'AMBIGUOUS'
            if expected!=status:raise ValueError('upstream status inconsistency')
            groups={}
            for i in inds:groups.setdefault(keys[i],[]).append(i)
            geo_groups=[sorted(x) for x in groups.values()]
            geo_groups.sort(key=lambda x:x[0])
            if len(inds)>1:
                if len(groups)==1: equivalent+=1; diagnosis='DUPLICATE_GEOMETRY_ONLY'
                else:competing+=1;diagnosis='DISTINCT_GEOMETRIC_ALTERNATIVES'
            elif len(inds)==1:diagnosis='ONE_SOURCE_LINE_DESCRIPTIVE'
            else:diagnosis='NO_SOURCE_LINE'
            local_one+=status=='ONE';local_amb+=status=='AMBIGUOUS';local_none+=status=='NONE'
            rows.append({'edge_id':eid,'original_match_status':status,
                'source_segment_indices':inds,'equivalence_groups':geo_groups,
                'distinct_geometries':len(groups),'diagnosis':diagnosis,
                'selection':'UNRESOLVED','architectural_proof':'NOT_EVALUATED'})
        if (local_one!=c.get('unique_source_match_edges') or local_amb!=c.get('ambiguous_source_match_edges') or local_none!=c.get('unmatched_top_edges')):
            raise ValueError('candidate totals mismatch')
        total+=len(items);one+=local_one;ambiguous+=local_amb;no+=local_none
        output.append({'candidate_id':cid,'top_edges':len(items),'evidence':rows,
                       'wall_identity':'NOT_EVALUATED','source_selection':'UNRESOLVED'})
    attr=prior.get('source_attribution',{})
    if (total!=prior.get('input_counts',{}).get('top_edges') or one!=attr.get('top_edges_one_match') or ambiguous!=attr.get('top_edges_ambiguous') or no!=attr.get('top_edges_no_match')):
        raise ValueError('global totals mismatch')
    return {'schema':SCHEMA,'status':'GEOMETRIC_EQUIVALENCE_DIAGNOSTIC_ONLY',
            'counts':{'candidate_groups':len(output),'top_edges':total,'one_match':one,
                      'original_ambiguous':ambiguous,'no_match':no,
                      'ambiguous_duplicate_geometry_only':equivalent,
                      'ambiguous_distinct_geometry':competing,
                      'ambiguities_architecturally_resolved':0},
            'candidate_evidence':output,
            'method':'R4 segment endpoint equivalence at 0.01 mm XY grid; orientation insensitive; never implies architectural equivalence',
            'gates':{'coordinate_registration':'UNVERIFIED','wall_classification':'NOT_EVALUATED',
                     'missing_wall_length':'NOT_EVALUATED','openings':'NOT_EVALUATED',
                     'architectural_approval':'LOCKED','do_release':'LOCKED'}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True);p.add_argument('--attribution',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    try:
        result=analyze(json.loads(Path(a.source).read_text(encoding='utf-8')),
                       json.loads(Path(a.attribution).read_text(encoding='utf-8')))
        result['sha256']={'source':digest(a.source),'attribution':digest(a.attribution)}
        code=0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        result={'schema':SCHEMA,'status':'BLOCKED','reason':str(exc),'gates':{'do_release':'LOCKED'}}
        code=2
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('PHOENIX_AF_R3_6_STATUS='+result['status'])
    print('REPORT='+str(output))
    return code
if __name__=='__main__':raise SystemExit(main())
