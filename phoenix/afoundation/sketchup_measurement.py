"""AF-R3.2: validate native SketchUp measurements; never infer verified walls.

Does NOT feed 3D projections into AF-R3 2D comparison without separate approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'phoenix.af_r3_2.sketchup_measurement.v1'
CLASSIFICATIONS = {'SOURCE_2D_DRAWING_UNVERIFIED','UNKNOWN_FLAT_UNVERIFIED','MODEL_3D_GEOMETRY_UNVERIFIED','UNKNOWN_UNVERIFIED'}

def validate(data):
    if data.get('schema') != SCHEMA or data.get('units') != 'mm' or data.get('coordinate_system') != 'sketchup_world_xyz_no_alignment_asserted':
        raise ValueError('Unrecognized source schema, units, or unproven coordinate registration')
    if data.get('measurement_status') != 'MEASURED_GEOMETRY_NOT_ARCHITECTURALLY_VERIFIED':
        raise ValueError('Unrecognized measurement status')
    if data.get('walls_verified') is not False or data.get('do_release') != 'LOCKED':
        raise ValueError('Unsafe approval or release claim')
    if not isinstance(data.get('edges'), list) or not data['edges']:
        raise ValueError('No measured edges')
    if data.get('edge_count') != len(data['edges']):
        raise ValueError('Inconsistent edge count')
    counts = {s:0 for s in sorted(CLASSIFICATIONS)}
    lengths = {s:0.0 for s in sorted(CLASSIFICATIONS)}
    seen=set()
    for edge in data['edges']:
        cat=edge.get('classification')
        if cat not in CLASSIFICATIONS:
            raise ValueError('Unrecognized classification')
        identifier=edge.get('id')
        if not isinstance(identifier,str) or not identifier or identifier in seen:
            raise ValueError('Duplicate or missing instance-path identity')
        seen.add(identifier)
        vertices=edge.get('vertices_mm')
        if not isinstance(vertices,list) or len(vertices)!=2 or any(not isinstance(p,list) or len(p)!=3 for p in vertices):
            raise ValueError('Malformed edge')
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for p in vertices for v in p):
            raise ValueError('Nonfinite geometry')
        length=math.dist(*vertices)
        if length < 0.00001:
            raise ValueError('Degenerate edge')
        reported=edge.get('length_3d_mm')
        if not isinstance(reported,(int,float)) or not math.isfinite(reported) or abs(reported-length)>0.02:
            raise ValueError('Invalid measured length')
        counts[cat]+=1
        lengths[cat]+=length
    if dict(data.get('classification_counts',{})) != {k:v for k,v in counts.items() if v}:
        raise ValueError('Classification totals inconsistent')
    return {'schema':'phoenix.af_r3_2.measurement_qa.v1',
            'status':'MEASUREMENT_QA_PASS_ARCHITECTURE_NOT_EVALUATED',
            'model_sha256':data.get('source_model_sha256'),
            'edge_count':len(seen),'classification_counts':{k:v for k,v in counts.items() if v},
            'length_by_class_mm':{k:round(v,3) for k,v in lengths.items() if v},
            'coordinate_alignment':'NOT_EVALUATED',
            'wall_identity':'NOT_EVALUATED','walls_3d':'NOT_EVALUATED',
            'source_2d_coverage':'NOT_EVALUATED','openings':'NOT_EVALUATED',
            'do_release':'LOCKED'}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    output=Path(a.output)
    try:
        source=Path(a.input)
        data=json.loads(source.read_text(encoding='utf-8'))
        report=validate(data)
        report['input_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        rc=0
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        report={'schema':'phoenix.af_r3_2.measurement_qa.v1','status':'BLOCKED','reason':f'{type(exc).__name__}: {exc}','do_release':'LOCKED'}
        rc=2
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PHOENIX_AF_R3_2_STATUS='+report['status'])
    print('REPORT='+str(output))
    return rc
if __name__=='__main__':
    raise SystemExit(main())
