"""Adapter from the central geometric model to production configuration."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

def derive_production_config(base:Mapping[str,Any],model:Mapping[str,Any])->dict[str,Any]:
    config=deepcopy(dict(base)); objects=model['objects']
    extension=next(item for item in objects if item['id']=='BLD-EXTENSION')
    points=extension['geometry']['points']; xs=[p[0] for p in points]; ys=[p[1] for p in points]
    config['version']='1.1.0'; config['issue_id']='HBM-CONCEPT-ISSUE-2026-002'
    config['geometry']['extension_width_m']=round(max(xs)-min(xs),3); config['geometry']['extension_length_m']=round(max(ys)-min(ys),3)
    config['geometry']['storeys']=extension['storeys']; config['geometry']['gross_area_m2']=round((max(xs)-min(xs))*(max(ys)-min(ys))*extension['storeys'],3)
    config['parking']['confirmed_capacity_spaces']=sum(item['space_count'] for item in objects if item['type']=='parking_zone')
    config['model_provenance']={'model_id':model['model_id'],'model_fingerprint_sha256':model['model_fingerprint_sha256'],'geometry_source':'central_geometric_project_model_v1_0_0','object_count':len(objects)}
    return config
