from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Mapping
from phoenix.cost_carbon import CostCarbonContext, CostCarbonEngine, LifecycleProfile, VariantInput
ADAPTER_ID="phoenix.adapter.cost_carbon_optimization.wave15_3"; ADAPTER_VERSION="1.0.0"
def run_cost_carbon_optimization(request:Mapping[str,Any],output_path:str|Path|None=None)->dict[str,Any]:
    c=dict(request['context']); p=dict(request.get('profile',{}))
    context=CostCarbonContext(str(c['project_id']),str(c.get('currency','EUR')),str(c.get('carbon_unit','kgCO2e')))
    profile=LifecycleProfile(int(p.get('analysis_years',50)),float(p.get('discount_rate',0.03)),float(p.get('annual_maintenance_fraction',0.01)),None if p.get('replacement_interval_years') is None else int(p['replacement_interval_years']),float(p.get('replacement_cost_fraction',1.0)),float(p.get('replacement_carbon_fraction',1.0)))
    variants=tuple(VariantInput(str(i['variant_id']),float(i['initial_cost']),float(i['embodied_carbon_kgco2e']),float(i.get('annual_operational_cost',0)),float(i.get('annual_operational_carbon_kgco2e',0)),float(i.get('salvage_value_fraction',0)),dict(i.get('attributes',{}))) for i in request['variants'])
    result=CostCarbonEngine().evaluate(context=context,profile=profile,variants=variants); result['adapter']={"id":ADAPTER_ID,"version":ADAPTER_VERSION}
    if output_path is not None:
        path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return result
