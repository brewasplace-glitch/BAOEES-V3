from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import hashlib, json, os, urllib.request
from phoenix.autonomy.european_certified_supply_priority import european_discovery_queries
# PHOENIX_EUROPEAN_DISCOVERY_QUERY_PRIORITY_v1_0

VERSION = "1.0.0"
FAMILIES = {"masonry_unit","structural_concrete","reinforcement_steel","structural_timber","structural_steel_section"}
TERMS = {
 "reinforcement_steel":["certified reinforcement steel B500B EN 10080","reinforcing bar mill certificate"],
 "structural_timber":["C24 structural timber EN 338 certificate","strength graded structural lumber"],
 "masonry_unit":["loadbearing masonry block compressive strength certificate"],
 "structural_concrete":["certified structural concrete product technical datasheet"],
 "structural_steel_section":["S355 structural steel EN 10025 certificate"],
}
@dataclass
class AcquisitionResult:
    status:str; register:dict[str,Any]; request_register:dict[str,Any]; written_catalogs:list[str]; blockers:list[dict[str,Any]]

def _read(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding="utf-8"));
    if not isinstance(v,dict): raise ValueError(f"JSON object required: {p}")
    return v

def _write(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _repo_ref(path:Path,repository:Path)->str:
    try:return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:return str(path.resolve())

def _dest(ctx:dict[str,Any])->dict[str,Any]:
    f=ctx.get("facts") if isinstance(ctx,dict) else {};f=f if isinstance(f,dict) else {}
    return {"country_code":str(f.get("country_code") or "").upper() or None,"city":f.get("municipality") or f.get("city") or "Paramaribo","location":f.get("project_location") or f.get("location") or "Paramaribo, Suriname","currency":str(f.get("currency") or "SRD").upper()}

def unresolved(local:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for r in local.get("selections") or []:
        if not isinstance(r,dict) or str(r.get("material_family") or "") not in FAMILIES: continue
        p=r.get("selected_product") if isinstance(r.get("selected_product"),dict) else {}
        q=str(r.get("engineering_qualification_status") or "").upper() in {"QUALIFIED","ENGINEERING_QUALIFIED"} and bool(p.get("engineering_material_id"))
        if not q: out.append(r)
    return out

def build_request_register(project_id:str,ctx:dict[str,Any],local:dict[str,Any])->dict[str,Any]:
    d=_dest(ctx);rows=[]
    for r in unresolved(local):
        fam=str(r.get("material_family") or "")
        base_queries=[f"{t} supplier price delivery {d['city']} Suriname" for t in TERMS.get(fam,[fam.replace('_',' ')])]
        queries=[q for base in base_queries for q in european_discovery_queries(base,fam)]
        rows.append({"requirement_id":r.get("requirement_id"),"material_family":fam,"element_role":r.get("element_role"),"queries":queries,"discovery_priority":["NL","BE","EU27","GLOBAL"],"required_evidence":["supplier_identity","product_identity","availability","engineering_material_id","technical_properties","certification","current_price","origin_country","hs_code","freight_to_destination","insurance","customs_duty","import_tax","brokerage","last_mile","current_fx_if_needed"]})
    return {"schema_version":"phoenix.global-supplier-discovery-request-register/1.0","project_id":project_id,"created_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"destination":d,"request_count":len(rows),"requests":rows,"automatic_ordering":False,"production_release":"LOCKED"}

def _cfg(repo:Path,name:str)->dict[str,Any]:
    p=repo/"configs"/"phoenix"/name
    try:return _read(p) if p.is_file() else {}
    except Exception:return {}

def _expand(s:str,m:dict[str,Any])->str:
    for k,v in m.items():s=s.replace("{"+k+"}",quote_plus(str(v or "")))
    return s

def _fetch(provider:dict[str,Any],url:str,body:dict[str,Any]|None,timeout:int,max_bytes:int)->tuple[Any,str]:
    headers={"User-Agent":"Project-Phoenix/3.0 supplier-acquisition"}
    env=provider.get("api_key_env");hdr=provider.get("api_key_header")
    if env and hdr and os.environ.get(str(env)):headers[str(hdr)]=str(provider.get("api_key_prefix") or "")+os.environ[str(env)]
    data=json.dumps(body).encode() if body is not None else None
    if data:headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=headers,method=str(provider.get("method") or ("POST" if data else "GET")).upper())
    with urllib.request.urlopen(req,timeout=timeout) as res:
        raw=res.read(max_bytes+1);ct=str(res.headers.get("Content-Type") or "")
    if len(raw)>max_bytes:raise ValueError("PROVIDER_RESPONSE_TOO_LARGE")
    if "json" not in ct.lower():raise ValueError("STRUCTURED_JSON_PROVIDER_REQUIRED")
    return json.loads(raw.decode("utf-8")),ct

def _rows(v:Any)->list[dict[str,Any]]:
    if isinstance(v,list):return [x for x in v if isinstance(x,dict)]
    if isinstance(v,dict):
        for k in ("products","items","offers","results","candidates"):
            if isinstance(v.get(k),list):return [x for x in v[k] if isinstance(x,dict)]
        if isinstance(v.get("web"),dict) and isinstance(v["web"].get("results"),list):return [x for x in v["web"]["results"] if isinstance(x,dict)]
        if isinstance(v.get("organic"),list):return [x for x in v["organic"] if isinstance(x,dict)]
        return [v]
    return []

def _candidate(row:dict[str,Any],fam:str,url:str,provider:str)->dict[str,Any]:
    c=dict(row);c.setdefault("material_family",fam);c.setdefault("source_url",url);c.setdefault("source_name",provider);c.setdefault("source_kind","configured_provider");c.setdefault("availability_verified_date",date.today().isoformat());c.setdefault("technical_properties",{});c.setdefault("certifications",[])
    if c.get("unit_price") is not None:c.setdefault("price_date",date.today().isoformat())
    return c

def _manifest_providers(manifest:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for field,cat in (("global_supplier_discovery_urls","SUPPLIER_CATALOG"),("certification_source_urls","CERTIFICATION"),("freight_quote_source_urls","FREIGHT"),("customs_source_urls","CUSTOMS")):
        for i,url in enumerate(manifest.get(field) or []):
            if isinstance(url,str) and url.startswith("https://"):out.append({"provider_id":f"MANIFEST_{cat}_{i+1}","category":cat,"enabled":True,"method":"GET","url_template":url})
    return out

def _match(rows:list[dict[str,Any]],c:dict[str,Any])->dict[str,Any]|None:
    for r in rows:
        if r.get("product_id") and str(r.get("product_id"))==str(c.get("product_id")):return r
        if r.get("material_family") and str(r.get("material_family"))==str(c.get("material_family")):return r
    return None

def acquire_global_supplier_import_evidence(*,repository:Path,workspace:Path,project_id:str,project_context:dict[str,Any],local_selection_register:dict[str,Any],manifest:dict[str,Any],policy:dict[str,Any]|None=None)->AcquisitionResult:
    repository=Path(repository).resolve();workspace=Path(workspace).resolve();policy=dict(policy or _cfg(repository,"global_supplier_discovery_import_acquisition_policy_v1_0.json") or {});reg=_cfg(repository,"global_supplier_discovery_provider_registry_v1_0.json");providers=[x for x in reg.get("providers") or [] if isinstance(x,dict)]+_manifest_providers(manifest);reqreg=build_request_register(project_id,project_context,local_selection_register);dest=reqreg["destination"];timeout=int(policy.get("https_timeout_seconds",15));maxb=int(policy.get("https_max_bytes",5000000));runs=[];candidates=[]
    for p in providers:
        if not p.get("enabled",False) or str(p.get("category") or "").upper() not in {"SUPPLIER_DISCOVERY","SUPPLIER_CATALOG"}:continue
        env=p.get("api_key_env")
        if env and not os.environ.get(str(env)):runs.append({"provider_id":p.get("provider_id"),"status":"SKIPPED_MISSING_CREDENTIAL","credential_env":env});continue
        for req in reqreg["requests"]:
            for query in req["queries"]:
                m={"query":query,"material_family":req["material_family"],"requirement_id":req.get("requirement_id"),"destination_city":dest["city"],"destination_country":dest["country_code"]};url=_expand(str(p.get("url_template") or ""),m)
                if not url:continue
                body=p.get("body_template") if isinstance(p.get("body_template"),dict) else None
                if body:
                    body={k:_expand(v,m) if isinstance(v,str) else v for k,v in body.items()}
                try:
                    data,_=_fetch(p,url,body,timeout,maxb);rs=_rows(data);runs.append({"provider_id":p.get("provider_id"),"requirement_id":req.get("requirement_id"),"query":query,"status":"ACQUIRED","url":url,"row_count":len(rs)})
                    if str(p.get("response_mode") or "PRODUCT_ROWS").upper()=="PRODUCT_ROWS":candidates.extend(_candidate(r,req["material_family"],url,str(p.get("provider_id"))) for r in rs)
                except Exception as exc:runs.append({"provider_id":p.get("provider_id"),"requirement_id":req.get("requirement_id"),"query":query,"status":"FAILED","url":url,"error":str(exc)})
    # enrichment providers attach only explicit structured evidence
    for c in candidates:
        params={"product_id":c.get("product_id"),"material_family":c.get("material_family"),"origin_country":c.get("country_code") or c.get("origin_country_code"),"destination_city":dest["city"],"destination_country":dest["country_code"],"hs_code":c.get("hs_code")}
        for cat in ("CERTIFICATION","FREIGHT","CUSTOMS"):
            for p in providers:
                if not p.get("enabled",False) or str(p.get("category") or "").upper()!=cat:continue
                url=_expand(str(p.get("url_template") or ""),params)
                if not url:continue
                try:
                    data,_=_fetch(p,url,None,timeout,maxb);row=_match(_rows(data),c)
                    if not row:continue
                    if cat=="CERTIFICATION":
                        if isinstance(row.get("technical_properties"),dict):c.setdefault("technical_properties",{}).update(row["technical_properties"])
                        if isinstance(row.get("certifications"),list):c.setdefault("certifications",[]).extend(row["certifications"])
                        c["engineering_material_id"]=c.get("engineering_material_id") or row.get("engineering_material_id");c["hs_code"]=c.get("hs_code") or row.get("hs_code")
                    elif cat=="FREIGHT":
                        if isinstance(row.get("logistics"),dict):c.setdefault("logistics",{}).update(row["logistics"])
                        if row.get("lead_time_days") is not None:c["lead_time_days"]=row["lead_time_days"]
                        if row.get("landed_cost_total_srd") is not None:c["landed_cost"]={"landed_cost_total_srd":row["landed_cost_total_srd"],"delivered_to":row.get("delivered_to") or dest["city"]}
                    else:
                        for k in ("hs_code","duty_amount","duty_rate","duty_basis","tax_amount","tax_rate","tax_basis","statistical_fee_amount","other_import_charges"):
                            if row.get(k) is not None:c[k]=row[k]
                        c["customs_source_url"]=url;c["customs_as_of_date"]=row.get("as_of_date") or date.today().isoformat()
                    runs.append({"provider_id":p.get("provider_id"),"category":cat,"product_id":c.get("product_id"),"status":"MATCHED","url":url})
                except Exception as exc:runs.append({"provider_id":p.get("provider_id"),"category":cat,"product_id":c.get("product_id"),"status":"FAILED","url":url,"error":str(exc)})
    source=workspace/"sources"/"global_material_supply"/"acquired";written=[]
    if candidates:
        p=source/f"GLOBAL_IMPORT_DISCOVERY_{date.today().strftime('%Y%m%d')}.json";_write(p,{"schema_version":"phoenix.global-import-discovered-product-catalog/1.0","project_id":project_id,"metadata":{"availability_verified_date":date.today().isoformat(),"destination":dest,"automatic_ordering":False},"products":candidates});written.append(_repo_ref(p,repository))
    active=any(p.get("enabled",False) and str(p.get("category") or "").upper() in {"SUPPLIER_DISCOVERY","SUPPLIER_CATALOG"} and (not p.get("api_key_env") or os.environ.get(str(p.get("api_key_env")))) for p in providers);blockers=[]
    if reqreg["request_count"] and not active:blockers.append({"reason":"GLOBAL_SUPPLIER_DISCOVERY_PROVIDER_REQUIRED"})
    if reqreg["request_count"] and active and not candidates:blockers.append({"reason":"NO_STRUCTURED_GLOBAL_PRODUCT_EVIDENCE_ACQUIRED"})
    fam={str(c.get("material_family") or "") for c in candidates}
    for r in reqreg["requests"]:
        if r["material_family"] not in fam:blockers.append({"requirement_id":r.get("requirement_id"),"material_family":r["material_family"],"reason":"GLOBAL_PRODUCT_CANDIDATE_REQUIRED"})
    status="PASSED" if (not reqreg["request_count"] or (candidates and not blockers)) else "BLOCKED";out={"schema_version":"phoenix.global-supplier-import-acquisition-register/1.0","engine_version":VERSION,"project_id":project_id,"status":status,"destination":dest,"provider_count":len(providers),"active_supplier_discovery_provider":active,"request_count":reqreg["request_count"],"candidate_count":len(candidates),"written_catalogs":written,"provider_runs":runs,"blockers":blockers,"implicit_search_engine":False,"certification_fabrication":False,"hs_code_fabrication":False,"freight_fabrication":False,"customs_rate_fabrication":False,"automatic_ordering":False,"automatic_payment":False,"professional_review_required":True,"production_release":"LOCKED"};rd=workspace/"sources"/"import_acquisition";_write(rd/"global_supplier_discovery_request_register.json",reqreg);_write(rd/"global_supplier_import_acquisition_register.json",out);return AcquisitionResult(status,out,reqreg,written,blockers)

# PHOENIX_STRUCTURED_PRODUCT_EVIDENCE_INTEGRATION_v1_0
# Search results are discovery-only. Direct source evidence is required before engineering qualification.
import functools as _phoenix_structured_evidence_functools
from phoenix.autonomy.structured_product_evidence_acquisition import enhance_acquisition_result as _phoenix_structured_evidence_enhance

_phoenix_structured_evidence_original_acquire_global_supplier_import_evidence = acquire_global_supplier_import_evidence

@_phoenix_structured_evidence_functools.wraps(_phoenix_structured_evidence_original_acquire_global_supplier_import_evidence)
def acquire_global_supplier_import_evidence(*args, **kwargs):
    _phoenix_base_result = _phoenix_structured_evidence_original_acquire_global_supplier_import_evidence(*args, **kwargs)
    try:
        return _phoenix_structured_evidence_enhance(_phoenix_base_result, args=args, kwargs=kwargs)
    except Exception as _phoenix_structured_evidence_exc:
        # Fail-safe: never turn an acquisition error into a pass. Do not expose credentials or source bodies.
        if isinstance(_phoenix_base_result, dict):
            _phoenix_base_result["structured_product_evidence_enabled"] = True
            _phoenix_base_result["structured_product_evidence_runtime_status"] = "BLOCKED"
            _phoenix_base_result["structured_product_evidence_runtime_error"] = type(_phoenix_structured_evidence_exc).__name__
            _phoenix_base_result["production_release"] = "LOCKED"
        return _phoenix_base_result
# END PHOENIX_STRUCTURED_PRODUCT_EVIDENCE_INTEGRATION_v1_0
