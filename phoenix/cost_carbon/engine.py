from __future__ import annotations
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json, math
from pathlib import Path
from typing import Any, Iterable, Mapping
ENGINE_ID="phoenix.cost_carbon_optimization.wave15_3"
ENGINE_VERSION="1.0.0"
SCHEMA_VERSION="1.0"
class CostCarbonError(ValueError): pass
@dataclass(frozen=True)
class LifecycleProfile:
    analysis_years:int=50
    discount_rate:float=0.03
    annual_maintenance_fraction:float=0.01
    replacement_interval_years:int|None=None
    replacement_cost_fraction:float=1.0
    replacement_carbon_fraction:float=1.0
    def validate(self):
        if self.analysis_years<=0: raise CostCarbonError("analysis_years must be positive.")
        for n,v in {"discount_rate":self.discount_rate,"annual_maintenance_fraction":self.annual_maintenance_fraction,"replacement_cost_fraction":self.replacement_cost_fraction,"replacement_carbon_fraction":self.replacement_carbon_fraction}.items():
            if not math.isfinite(v) or v<0: raise CostCarbonError(f"{n} must be finite and non-negative.")
        if self.replacement_interval_years is not None and self.replacement_interval_years<=0: raise CostCarbonError("replacement_interval_years must be positive when supplied.")
@dataclass(frozen=True)
class VariantInput:
    variant_id:str
    initial_cost:float
    embodied_carbon_kgco2e:float
    annual_operational_cost:float=0.0
    annual_operational_carbon_kgco2e:float=0.0
    salvage_value_fraction:float=0.0
    attributes:Mapping[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.variant_id.strip(): raise CostCarbonError("variant_id must not be empty.")
        vals={"initial_cost":self.initial_cost,"embodied_carbon_kgco2e":self.embodied_carbon_kgco2e,"annual_operational_cost":self.annual_operational_cost,"annual_operational_carbon_kgco2e":self.annual_operational_carbon_kgco2e,"salvage_value_fraction":self.salvage_value_fraction}
        for n,v in vals.items():
            if not math.isfinite(v) or v<0: raise CostCarbonError(f"{n} must be finite and non-negative.")
        if self.salvage_value_fraction>1: raise CostCarbonError("salvage_value_fraction must not exceed 1.")
@dataclass(frozen=True)
class CostCarbonContext:
    project_id:str
    currency:str="EUR"
    carbon_unit:str="kgCO2e"
    def validate(self):
        if not self.project_id.strip(): raise CostCarbonError("project_id must not be empty.")
        if not self.currency.strip() or not self.carbon_unit.strip(): raise CostCarbonError("currency and carbon_unit must not be empty.")
class CostCarbonEngine:
    @staticmethod
    def _canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
    @classmethod
    def _digest(cls,v): return sha256(cls._canonical_json(v).encode()).hexdigest()
    @staticmethod
    def _df(rate,year): return 1/((1+rate)**year)
    def evaluate(self,*,context,profile,variants):
        context.validate(); profile.validate(); ordered=sorted(list(variants),key=lambda x:x.variant_id)
        if not ordered: raise CostCarbonError("At least one variant is required.")
        seen=set(); results=[]
        for var in ordered:
            var.validate()
            if var.variant_id in seen: raise CostCarbonError(f"Duplicate variant_id: {var.variant_id}")
            seen.add(var.variant_id)
            maint=op=rep=repco2=0.0
            for y in range(1,profile.analysis_years+1):
                d=self._df(profile.discount_rate,y)
                maint += var.initial_cost*profile.annual_maintenance_fraction*d
                op += var.annual_operational_cost*d
                if profile.replacement_interval_years and y%profile.replacement_interval_years==0 and y<profile.analysis_years:
                    rep += var.initial_cost*profile.replacement_cost_fraction*d
                    repco2 += var.embodied_carbon_kgco2e*profile.replacement_carbon_fraction
            salvage=var.initial_cost*var.salvage_value_fraction*self._df(profile.discount_rate,profile.analysis_years)
            lcc=var.initial_cost+maint+op+rep-salvage
            lca=var.embodied_carbon_kgco2e+var.annual_operational_carbon_kgco2e*profile.analysis_years+repco2
            results.append({"variant_id":var.variant_id,"initial_cost":round(var.initial_cost,6),"maintenance_cost_npv":round(maint,6),"operational_cost_npv":round(op,6),"replacement_cost_npv":round(rep,6),"salvage_value_npv":round(salvage,6),"lifecycle_cost":round(lcc,6),"embodied_carbon_kgco2e":round(var.embodied_carbon_kgco2e,6),"operational_carbon_kgco2e":round(var.annual_operational_carbon_kgco2e*profile.analysis_years,6),"replacement_carbon_kgco2e":round(repco2,6),"lifecycle_carbon_kgco2e":round(lca,6),"attributes":dict(var.attributes)})
        lowest_cost=min(results,key=lambda x:(x['lifecycle_cost'],x['variant_id']))['variant_id']
        lowest_carbon=min(results,key=lambda x:(x['lifecycle_carbon_kgco2e'],x['variant_id']))['variant_id']
        payload={"schema_version":SCHEMA_VERSION,"engine":{"id":ENGINE_ID,"version":ENGINE_VERSION},"project_id":context.project_id,"currency":context.currency,"carbon_unit":context.carbon_unit,"profile":asdict(profile),"variant_count":len(results),"variants":results,"lowest_lifecycle_cost_variant_id":lowest_cost,"lowest_lifecycle_carbon_variant_id":lowest_carbon,"optimization_contract":{"target_engine":"phoenix.optimization_core.wave15_1","metric_mapping":{"cost":"lifecycle_cost","carbon":"lifecycle_carbon_kgco2e"}},"limitations":["Input factors require project-specific verification.","No live price or EPD database is included.","MKI/MPG certification is not claimed.","Qualified review is required."]}
        payload['evidence']={"algorithm":"sha256","payload_sha256":self._digest(payload)}
        return payload
    def write_result(self,*,context,profile,variants,destination):
        result=self.evaluate(context=context,profile=profile,variants=variants)
        p=Path(destination); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); t.replace(p); return p
