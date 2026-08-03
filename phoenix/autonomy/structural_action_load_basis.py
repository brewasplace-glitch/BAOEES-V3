"""Phoenix Autonomous Structural Action & Load Basis Engine v1.0.

The engine selects a current, jurisdiction-matching engineering load source and
normalizes its explicit `action_load_input` for Phoenix v8.2. It never invents
norm values, wind values, imposed loads, combination factors, or code status.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

VERSION="1.0.0"

@dataclass
class ActionLoadBasisResult:
    status:str
    action_load_input:dict[str,Any]|None
    source_register:dict[str,Any]
    blockers:list[dict[str,Any]]
    warnings:list[str]

def _read(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):raise ValueError("JSON root must be object")
    return value

def _date(value:Any)->date|None:
    if not value:return None
    try:return date.fromisoformat(str(value)[:10])
    except ValueError:return None

def _norm(value:Any)->str:
    return str(value or "").strip().casefold()

def _policy(repository:Path)->dict[str,Any]:
    path=repository/"configs"/"phoenix"/"structural_action_load_basis_policy_v1_0.json"
    return _read(path) if path.is_file() else {"freshness":{"default_max_age_days":3650}}

def _sources(repository:Path,project_id:str)->list[Path]:
    roots=[
        repository/"inputs"/"structural_action_load",
        repository/"data"/"structural_action_load",
        repository/"configs"/"phoenix"/"structural_action_load_catalog",
    ]
    result=[]
    for root in roots:
        if root.is_dir():
            result.extend(p for p in root.rglob("*.json") if p.is_file())
    return sorted(set(result))

def _geo(project_context:dict[str,Any])->dict[str,Any]:
    facts=project_context.get("facts") or {}
    return {
        "country_code":str(facts.get("country_code") or "").upper().strip() or None,
        "region_name":facts.get("region"),
        "municipality":facts.get("municipality"),
    }

def _validate_source(
    value:dict[str,Any],
    *,
    geography:dict[str,Any],
    as_of:date,
    max_age_days:int,
)->tuple[bool,dict[str,Any]]:
    md=value.get("metadata") if isinstance(value.get("metadata"),dict) else value
    action=value.get("action_load_input")
    if not isinstance(action,dict):
        return False,{"reason":"ACTION_LOAD_INPUT_OBJECT_REQUIRED"}
    country=str(md.get("country_code") or "").upper().strip()
    if not country:
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_COUNTRY_REQUIRED"}
    if country!=geography.get("country_code"):
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_COUNTRY_MISMATCH","country_code":country}
    region=md.get("region_name") or md.get("region")
    if region and geography.get("region_name") and _norm(region)!=_norm(geography["region_name"]):
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_REGION_MISMATCH"}
    municipality=md.get("municipality") or md.get("city")
    if municipality and geography.get("municipality") and _norm(municipality)!=_norm(geography["municipality"]):
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_MUNICIPALITY_MISMATCH"}

    effective=_date(md.get("effective_date"))
    valid_until=_date(md.get("valid_until"))
    status=str(md.get("status") or "").upper().strip()
    if effective is None:
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_EFFECTIVE_DATE_REQUIRED"}
    if effective>as_of:
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_EFFECTIVE_DATE_IN_FUTURE"}
    age=(as_of-effective).days
    if valid_until is not None:
        if valid_until<as_of:
            return False,{"reason":"STRUCTURAL_LOAD_SOURCE_EXPIRED"}
        current_basis="VALID_UNTIL"
    elif status=="ACTIVE":
        if age>max_age_days:
            return False,{"reason":"STRUCTURAL_LOAD_SOURCE_CURRENT_STATUS_REVIEW_REQUIRED"}
        current_basis="ACTIVE_STATUS"
    else:
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_CURRENT_STATUS_REQUIRED"}

    for field in ("basis","unit_system","actions","combinations"):
        if field not in action:
            return False,{"reason":"STRUCTURAL_ACTION_LOAD_INPUT_INCOMPLETE","field":field}
    if not isinstance(action.get("actions"),list) or not action["actions"]:
        return False,{"reason":"STRUCTURAL_ACTIONS_REQUIRED"}
    if not isinstance(action.get("combinations"),list) or not action["combinations"]:
        return False,{"reason":"STRUCTURAL_LOAD_COMBINATIONS_REQUIRED"}
    if not any(str(x.get("kind") or "").lower()=="self_weight" for x in action["actions"] if isinstance(x,dict)):
        return False,{"reason":"STRUCTURAL_SELF_WEIGHT_ACTION_REQUIRED"}
    source_name=md.get("source_name") or md.get("publisher")
    if not source_name:
        return False,{"reason":"STRUCTURAL_LOAD_SOURCE_NAME_REQUIRED"}

    score=1000+max(0,500-min(age,500))
    if municipality and geography.get("municipality"):score+=2000
    elif region and geography.get("region_name"):score+=1000
    return True,{
        "metadata":{
            "source_name":source_name,
            "source_url":md.get("source_url"),
            "basis_id":md.get("basis_id") or md.get("id"),
            "country_code":country,
            "region_name":region,
            "municipality":municipality,
            "effective_date":effective.isoformat(),
            "valid_until":valid_until.isoformat() if valid_until else None,
            "status":status or None,
            "current_status_basis":current_basis,
            "selection_score":score,
        },
        "action_load_input":action,
    }

def build_structural_action_load_basis(
    *,
    repository:Path,
    project_id:str,
    project_context:dict[str,Any],
    as_of_date:str|date|None=None,
)->ActionLoadBasisResult:
    repository=repository.resolve()
    if isinstance(as_of_date,date):as_of=as_of_date
    elif as_of_date:as_of=_date(as_of_date) or date.today()
    else:as_of=date.today()
    geography=_geo(project_context)
    blockers=[]
    warnings=[]
    if not geography["country_code"]:
        blockers.append({
            "reason":"PROJECT_JURISDICTION_REQUIRED_FOR_STRUCTURAL_LOAD_BASIS",
            "message":"Projectland/gebiedsdeel is vereist voor normatieve belastingsselectie.",
        })
        return ActionLoadBasisResult("BLOCKED",None,{
            "schema_version":"phoenix.structural-action-load-source-register/1.0",
            "project_id":project_id,"geography":geography,"candidates":[],"rejections":[],
            "production_release":"LOCKED",
        },blockers,warnings)

    policy=_policy(repository)
    max_age=int((policy.get("freshness") or {}).get("default_max_age_days",3650))
    accepted=[]
    rejected=[]
    for path in _sources(repository,project_id):
        try:value=_read(path)
        except Exception as exc:
            rejected.append({"source":str(path),"reason":"INVALID_JSON","message":str(exc)})
            continue
        ok,result=_validate_source(value,geography=geography,as_of=as_of,max_age_days=max_age)
        if ok:
            accepted.append({
                "source_reference":path.relative_to(repository).as_posix(),
                **result,
            })
        else:
            rejected.append({
                "source_reference":path.relative_to(repository).as_posix(),
                **result,
            })
    accepted.sort(key=lambda x:x["metadata"]["selection_score"],reverse=True)
    register={
        "schema_version":"phoenix.structural-action-load-source-register/1.0",
        "engine_version":VERSION,
        "project_id":project_id,
        "as_of_date":as_of.isoformat(),
        "geography":geography,
        "candidates":[{"source_reference":x["source_reference"],"metadata":x["metadata"]} for x in accepted],
        "rejections":rejected,
        "automatic_norm_value_invention":False,
        "automatic_combination_factor_invention":False,
        "production_release":"LOCKED",
    }
    if not accepted:
        blockers.append({
            "reason":"CURRENT_STRUCTURAL_ACTION_LOAD_BASIS_REQUIRED",
            "message":"Geen actuele, projectspecifieke en jurisdiction-matching belastings-/combinatiebron gevonden voor v8.2.",
            "country_code":geography["country_code"],
        })
        return ActionLoadBasisResult("BLOCKED",None,register,blockers,warnings)
    selected=accepted[0]
    register["selected"]={"source_reference":selected["source_reference"],"metadata":selected["metadata"]}
    action=json.loads(json.dumps(selected["action_load_input"]))
    action["source_evidence"]={
        **selected["metadata"],
        "source_reference":selected["source_reference"],
    }
    return ActionLoadBasisResult("PASSED",action,register,blockers,warnings)
