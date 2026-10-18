"""AF-R3.7: fail-closed CAD semantic evidence audit. Does not infer wall identity.

DXF conversion must be externally provenance-linked to the immutable original DWG.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

SCHEMA = 'phoenix.af_r3_7.cad_semantic_gate.v1'
SOURCE_SHA = 'a4660e5631192af366c1a1c8a8c1ee5ccd7eed82f65cd710b7cafdf6e7b40189'
R36_SHA = 'fa7d42e4ea711abfcaac0aad471b21359c33019e'

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def validate_manifest(m):
    if not isinstance(m, dict): raise ValueError('manifest must be an object')
    if m.get('original_dwg_sha256') != SOURCE_SHA: raise ValueError('wrong original DWG identity')
    if m.get('conversion_method') not in ('ODA_FILE_CONVERTER', 'AUTOCAD_EXPORT', 'BRICSCAD_EXPORT'):
        raise ValueError('unsupported or unrecorded conversion method')
    if not isinstance(m.get('conversion_operator'), str) or not m['conversion_operator'].strip():
        raise ValueError('conversion operator missing')
    if not isinstance(m.get('dxf_sha256'), str) or len(m['dxf_sha256']) != 64 or any(c not in '0123456789abcdef' for c in m['dxf_sha256']):
        raise ValueError('invalid DXF checksum')
    if m.get('source_modified') is not False: raise ValueError('immutable DWG status unproven')
    return True

def audit(dwg=None, dxf=None, manifest=None):
    out = {
        'schema':SCHEMA, 'status':'WAITING_FOR_AUTHENTICATED_CAD_SEMANTICS',
        'baseline':R36_SHA, 'original_dwg_sha256_expected':SOURCE_SHA,
        'source_provenance':'UNVERIFIED', 'dxf_conversion':'NOT_SUPPLIED',
        'cad_semantic_evidence':'NOT_EVALUATED', 'source_layers':None,
        'source_blocks':None, 'entity_type_counts':None,
        'dimension_entity_count':None, 'insert_unit_code':None,
        'candidate_wall_names':[], 'wall_identity':'NOT_EVALUATED',
        'remaining_distinct_geometric_alternatives':72,
        'original_ambiguous_matches':75,
        'gates': {'coordinate_registration':'UNVERIFIED','wall_semantic_identity':'LOCKED',
                  'missing_wall_length':'NOT_EVALUATED','architectural_approval':'LOCKED',
                  'do_release':'LOCKED'},
        'notes':['Layer or block names are metadata clues, not proof of walls.',
                 'DXF without a source-linked conversion manifest must not be trusted.',
                 'An authenticated DXF still requires coordinate and wall-identity validation.']
    }
    if dwg is not None:
        p=Path(dwg)
        if not p.is_file():raise FileNotFoundError(p)
        with p.open('rb') as f: magic=f.read(6)
        out['dwg_magic']=magic.decode('ascii',errors='replace')
        out['dwg_sha256']=sha256(p)
        if magic != b'AC1015' or out['dwg_sha256'] != SOURCE_SHA:raise ValueError('original DWG identity mismatch')
        out['source_provenance']='IMMUTABLE_DWG_SHA256_VERIFIED'
    if dxf is None:
        if manifest is not None: raise ValueError('conversion manifest without DXF')
        return out
    if manifest is None or dwg is None: raise ValueError('DXF requires manifest AND verified original DWG')
    p=Path(dxf)
    if not p.is_file():raise FileNotFoundError(p)
    m=json.loads(Path(manifest).read_text(encoding='utf-8'))
    validate_manifest(m)
    if sha256(p)!=m['dxf_sha256']:raise ValueError('DXF digest mismatch')
    try:
        import ezdxf
    except ImportError as e:
        raise RuntimeError('ezdxf is required to inspect supplied DXF') from e
    doc=ezdxf.readfile(str(p))
    types=Counter()
    for entity in doc.modelspace():
        types[entity.dxftype()]+=1
    names=sorted({str(x.dxf.name) for x in doc.layers})
    blocks=sorted({str(x.name) for x in doc.blocks if not x.name.startswith('*')})
    if not names:raise ValueError('DXF missing layer table')
    out.update({
      'status':'CAD_SEMANTIC_INVENTORY_PROVENANCE_LINKED_ARCHITECTURE_UNVERIFIED',
      'dxf_conversion':'MANIFEST_AND_HASH_VERIFIED',
      'cad_semantic_evidence':'INVENTORIED_NOT_CLASSIFIED',
      'source_layers':names,'source_blocks':blocks,
      'entity_type_counts':dict(sorted(types.items())),
      'dimension_entity_count':types['DIMENSION'],
      'insert_unit_code':int(doc.header.get('$INSUNITS',0)),
      'dxf_sha256':sha256(p),'conversion_method':m['conversion_method']})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dwg');p.add_argument('--dxf');p.add_argument('--manifest');p.add_argument('--output',required=True)
    args=p.parse_args()
    report=audit(args.dwg,args.dxf,args.manifest)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PHOENIX_AF_R3_7_STATUS='+report['status'])
    print('REPORT='+args.output)
if __name__=='__main__':main()
