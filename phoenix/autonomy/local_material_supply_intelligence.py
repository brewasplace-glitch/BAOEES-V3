"""Phoenix Local Material, Product & Supply Intelligence Engine v1.0.

Purpose
-------
Make local/regional product availability an explicit engineering and release
constraint. Phoenix may create early concept geometry with generic material
families, but it may not treat structural materials/products as final or
release-ready unless local availability is evidenced.

Hard rules
----------
- UI locale never defines project geography or material market.
- City/region/country supply is preferred in that order.
- Local availability must have source + geography + verification date.
- Structural products require engineering_material_id + technical properties.
- Stale stock/availability evidence does not count as confirmed.
- Regional/international import is never silently treated as local.
- A material/product substitution always creates a recalculation/review flag.
- Supplier price is evidence, not a substitute for the Local Cost Intelligence gate.
- No supplier endpoint or current stock level is fabricated by Phoenix.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

VERSION = "1.0.0"

CONFIRMED_SOURCE_STATES = {"IN_STOCK", "AVAILABLE_TO_ORDER"}
PROBABLE_SOURCE_STATES = {"LIMITED_STOCK"}
UNAVAILABLE_SOURCE_STATES = {"OUT_OF_STOCK", "DISCONTINUED"}
STRUCTURAL_FAMILIES = {
    "structural_concrete",
    "reinforcement_steel",
    "structural_steel_section",
    "structural_timber",
    "masonry_unit",
}

@dataclass
class MaterialSupplyResult:
    status: str
    requirements: dict[str, Any]
    selection_register: dict[str, Any]
    supply_register: dict[str, Any]
    change_control: dict[str, Any]
    blockers: list[dict[str, Any]]
    warnings: list[str]

def _read_json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value

def _parse_date(value: Any) -> date | None:
    if value in (None,""):
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None

def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+","",str(value or "").strip().casefold())

def _policy(repository: Path) -> dict[str,Any]:
    path=repository/"configs"/"phoenix"/"local_material_supply_policy_v1_0.json"
    if path.is_file():
        return _read_json(path)
    return {
        "freshness":{"default_max_age_days":30},
        "selection":{"allow_probable_for_final":False,"allow_import_as_local":False},
        "remote":{"timeout_seconds":8,"maximum_bytes":5_000_000},
    }

def _source_registry(repository: Path) -> dict[str,Any]:
    path=repository/"configs"/"phoenix"/"material_supply_source_registry_v1_0.json"
    if path.is_file():
        return _read_json(path)
    return {"sources":[]}

def _load_remote_json(url: str, timeout: float, maximum_bytes: int) -> dict[str,Any]:
    if not url.lower().startswith("https://"):
        raise ValueError("Only HTTPS material/supply sources are allowed.")
    request=urllib.request.Request(url,headers={"User-Agent":"Project-Phoenix-Material-Supply/1.0"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=response.read(maximum_bytes+1)
    if len(raw)>maximum_bytes:
        raise ValueError("Remote material/supply source exceeds configured maximum size.")
    value=json.loads(raw.decode("utf-8"))
    if not isinstance(value,dict):
        raise ValueError("Remote material/supply JSON root must be an object.")
    return value

def _discover_catalogs(repository: Path, policy: dict[str,Any]) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    registry=_source_registry(repository)
    found=[]
    failures=[]
    remote=policy.get("remote") or {}
    timeout=float(remote.get("timeout_seconds",8))
    maximum_bytes=int(remote.get("maximum_bytes",5_000_000))
    for source in registry.get("sources",[]):
        if not isinstance(source,dict) or not source.get("enabled",False):
            continue
        source_id=str(source.get("source_id") or "UNNAMED")
        kind=str(source.get("kind") or "").lower()
        priority=int(source.get("priority",0))
        max_age=source.get("max_age_days")
        try:
            if kind=="filesystem_glob":
                for path in sorted(repository.glob(str(source.get("glob") or ""))):
                    if not path.is_file() or path.suffix.lower()!=".json":
                        continue
                    try:
                        found.append({
                            "source_id":source_id,
                            "source_kind":kind,
                            "source_priority":priority,
                            "source_max_age_days":max_age,
                            "source_reference":path.relative_to(repository).as_posix(),
                            "catalog":_read_json(path),
                        })
                    except Exception as exc:
                        failures.append({
                            "source_id":source_id,"reference":str(path),
                            "reason":"INVALID_MATERIAL_SUPPLY_CATALOG","message":str(exc)
                        })
            elif kind=="https_json":
                url=str(source.get("url") or "")
                found.append({
                    "source_id":source_id,
                    "source_kind":kind,
                    "source_priority":priority,
                    "source_max_age_days":max_age,
                    "source_reference":url,
                    "catalog":_load_remote_json(url,timeout,maximum_bytes),
                })
            else:
                failures.append({
                    "source_id":source_id,"reason":"UNSUPPORTED_SOURCE_KIND","message":kind
                })
        except Exception as exc:
            failures.append({
                "source_id":source_id,"reason":"SOURCE_FETCH_FAILED","message":str(exc)
            })
    return found,failures

def _project_geo(project_context: dict[str,Any], manifest: dict[str,Any]) -> dict[str,Any]:
    facts=(project_context.get("facts") or {}) if isinstance(project_context,dict) else {}
    return {
        "country_code":str(facts.get("country_code") or manifest.get("country_code") or "").upper().strip() or None,
        "region_name":facts.get("region") or manifest.get("region"),
        "municipality":facts.get("municipality") or manifest.get("municipality"),
        "location":facts.get("project_location") or manifest.get("location"),
        "currency":facts.get("currency") or manifest.get("currency"),
    }

def _candidate_family(value: Any, *, element: str) -> str | None:
    text=_norm(value)
    if not text:
        return None
    if "masonry" in text or "block" in text or "brick" in text:
        return "masonry_unit"
    if "reinforcedconcrete" in text or text in {"concrete","rc"}:
        return "structural_concrete"
    if "timber" in text or "wood" in text:
        return "structural_timber"
    if "steel" in text:
        return "structural_steel_section"
    if element in {"column","beam","slab"} and "concrete" in text:
        return "structural_concrete"
    return None

def derive_material_requirements(
    *,
    project_id: str,
    architectural_model: dict[str,Any],
    structural_profile: dict[str,Any],
) -> dict[str,Any]:
    assumptions=structural_profile.get("assumptions") or {}
    raw=[
        ("loadbearing_wall","default_wall_material",assumptions.get("default_wall_material")),
        ("column","default_column_material",assumptions.get("default_column_material")),
        ("slab","default_slab_material",assumptions.get("default_slab_material")),
        ("beam","default_beam_material",assumptions.get("default_beam_material")),
        ("roof_structure","default_roof_material",assumptions.get("default_roof_material")),
    ]
    requirements=[]
    seen=set()
    for element,key,value in raw:
        family=_candidate_family(value,element=element)
        if not family:
            continue
        rid=f"REQ-{element.upper().replace('_','-')}-{family.upper().replace('_','-')}"
        requirements.append({
            "requirement_id":rid,
            "element_role":element,
            "material_family":family,
            "source_profile_field":key,
            "source_candidate":value,
            "structural":family in STRUCTURAL_FAMILIES,
            "local_availability_required":True,
            "technical_properties_required":family in STRUCTURAL_FAMILIES,
        })
        seen.add(family)

    # Reinforced concrete implies reinforcement availability as a separate real product.
    if "structural_concrete" in seen and "reinforcement_steel" not in seen:
        requirements.append({
            "requirement_id":"REQ-REINFORCEMENT-STEEL",
            "element_role":"reinforcement",
            "material_family":"reinforcement_steel",
            "source_profile_field":"dependency_of_reinforced_concrete",
            "source_candidate":"reinforcement_steel_required",
            "structural":True,
            "local_availability_required":True,
            "technical_properties_required":True,
        })

    return {
        "schema_version":"phoenix.local-material-requirements/1.0",
        "project_id":project_id,
        "building_type":(architectural_model.get("building") or {}).get("type"),
        "requirements":requirements,
        "final_design_requires_all_confirmed":True,
        "import_is_not_local":True,
        "professional_review_required":True,
        "production_release":"LOCKED",
    }

def _catalog_metadata(catalog: dict[str,Any]) -> dict[str,Any]:
    value=catalog.get("metadata")
    return value if isinstance(value,dict) else catalog

def _catalog_scope(
    *,
    metadata: dict[str,Any],
    geography: dict[str,Any],
) -> tuple[str|None,int,str|None]:
    country=str(metadata.get("country_code") or "").upper().strip()
    region=metadata.get("region_name") or metadata.get("region")
    city=metadata.get("city") or metadata.get("municipality")
    project_country=geography.get("country_code")
    project_region=geography.get("region_name")
    project_city=geography.get("municipality")

    if not country:
        return None,0,"CATALOG_COUNTRY_REQUIRED"
    if country!=project_country:
        declared=str(metadata.get("market_scope") or "").upper()
        if declared=="REGIONAL_IMPORT":
            return "REGIONAL_IMPORT",100,None
        if declared=="INTERNATIONAL_IMPORT":
            return "INTERNATIONAL_IMPORT",50,None
        return None,0,"FOREIGN_CATALOG_NOT_DECLARED_AS_IMPORT"

    if city:
        if not project_city:
            return None,0,"PROJECT_CITY_REQUIRED_FOR_CITY_SUPPLY_CATALOG"
        if _norm(city)!=_norm(project_city):
            return None,0,"SUPPLY_CATALOG_CITY_MISMATCH"
        return "CITY",4000,None
    if region:
        if not project_region:
            return None,0,"PROJECT_REGION_REQUIRED_FOR_REGIONAL_SUPPLY_CATALOG"
        if _norm(region)!=_norm(project_region):
            return None,0,"SUPPLY_CATALOG_REGION_MISMATCH"
        return "REGION",3000,None
    return "COUNTRY",2000,None

def _freshness(
    *,
    verified: date | None,
    valid_until: date | None,
    as_of: date,
    max_age_days: int,
) -> tuple[bool,int|None,str]:
    if verified is None:
        return False,None,"VERIFIED_DATE_REQUIRED"
    if verified>as_of:
        return False,(verified-as_of).days,"VERIFICATION_DATE_IN_FUTURE"
    age=(as_of-verified).days
    if valid_until is not None:
        if valid_until<as_of:
            return False,age,"AVAILABILITY_EVIDENCE_EXPIRED"
        return True,age,"VALIDITY_WINDOW"
    if age>max_age_days:
        return False,age,"AVAILABILITY_EVIDENCE_STALE"
    return True,age,"AGE_LIMIT"

def _product_record(
    *,
    candidate: dict[str,Any],
    product: dict[str,Any],
    geography: dict[str,Any],
    as_of: date,
    policy: dict[str,Any],
) -> tuple[dict[str,Any]|None,dict[str,Any]|None]:
    md=_catalog_metadata(candidate["catalog"])
    scope,scope_score,scope_error=_catalog_scope(metadata=md,geography=geography)
    if scope_error:
        return None,{"reason":scope_error,"source_reference":candidate["source_reference"]}

    verified=_parse_date(
        product.get("availability_verified_date")
        or product.get("verified_date")
        or md.get("availability_verified_date")
        or md.get("verified_date")
    )
    valid_until=_parse_date(product.get("availability_valid_until") or md.get("availability_valid_until"))
    default_age=int((policy.get("freshness") or {}).get("default_max_age_days",30))
    source_age=candidate.get("source_max_age_days")
    max_age=int(source_age) if source_age not in (None,"") else default_age
    fresh,age,freshness_basis=_freshness(
        verified=verified,valid_until=valid_until,as_of=as_of,max_age_days=max_age
    )

    source_state=str(product.get("availability_status") or "UNKNOWN").upper().strip()
    if source_state in CONFIRMED_SOURCE_STATES and fresh:
        availability="LOCAL_AVAILABILITY_CONFIRMED" if scope in {"CITY","REGION","COUNTRY"} else (
            "REGIONAL_IMPORT_REQUIRED" if scope=="REGIONAL_IMPORT" else "INTERNATIONAL_IMPORT_REQUIRED"
        )
    elif source_state in PROBABLE_SOURCE_STATES and fresh:
        availability="LOCAL_AVAILABILITY_PROBABLE" if scope in {"CITY","REGION","COUNTRY"} else (
            "REGIONAL_IMPORT_REQUIRED" if scope=="REGIONAL_IMPORT" else "INTERNATIONAL_IMPORT_REQUIRED"
        )
    elif source_state in UNAVAILABLE_SOURCE_STATES:
        availability="UNAVAILABLE"
    else:
        availability="AVAILABILITY_UNKNOWN"

    technical=product.get("technical_properties")
    technical=technical if isinstance(technical,dict) else {}
    engineering_id=product.get("engineering_material_id")
    structural=str(product.get("material_family") or "") in STRUCTURAL_FAMILIES
    technical_ok=bool(engineering_id and technical) if structural else True

    score=scope_score+int(candidate.get("source_priority",0))
    if availability=="LOCAL_AVAILABILITY_CONFIRMED": score+=3000
    elif availability=="LOCAL_AVAILABILITY_PROBABLE": score+=1000
    elif availability=="REGIONAL_IMPORT_REQUIRED": score+=300
    elif availability=="INTERNATIONAL_IMPORT_REQUIRED": score+=100
    if age is not None: score+=max(0,500-min(age,500))
    if technical_ok: score+=250

    price_date=_parse_date(product.get("price_date"))
    price_valid_until=_parse_date(product.get("price_valid_until"))
    price=product.get("unit_price")
    try:
        price=float(price) if price is not None else None
    except (TypeError,ValueError):
        price=None

    normalized={
        "product_id":product.get("product_id"),
        "supplier_product_code":product.get("supplier_product_code"),
        "manufacturer":product.get("manufacturer"),
        "supplier_id":md.get("supplier_id"),
        "supplier_name":md.get("supplier_name") or md.get("source_name"),
        "description":product.get("description"),
        "material_family":product.get("material_family"),
        "engineering_material_id":engineering_id,
        "technical_properties":technical,
        "certifications":product.get("certifications") if isinstance(product.get("certifications"),list) else [],
        "unit":product.get("unit"),
        "availability_status":availability,
        "source_availability_status":source_state,
        "market_scope":scope,
        "lead_time_days":product.get("lead_time_days"),
        "minimum_order_quantity":product.get("minimum_order_quantity"),
        "country_code":md.get("country_code"),
        "region_name":md.get("region_name") or md.get("region"),
        "city":md.get("city") or md.get("municipality"),
        "availability_verified_date":verified.isoformat() if verified else None,
        "availability_valid_until":valid_until.isoformat() if valid_until else None,
        "availability_age_days":age,
        "freshness_basis":freshness_basis,
        "availability_evidence_fresh":fresh,
        "currency":str(product.get("currency") or md.get("currency") or "").upper().strip() or None,
        "unit_price":price,
        "price_date":price_date.isoformat() if price_date else None,
        "price_valid_until":price_valid_until.isoformat() if price_valid_until else None,
        "source_name":md.get("source_name") or md.get("supplier_name") or candidate["source_id"],
        "source_url":md.get("source_url"),
        "source_reference":candidate["source_reference"],
        "source_kind":candidate["source_kind"],
        "confidence":str(product.get("confidence") or md.get("confidence") or "MEDIUM").upper(),
        "structural_technical_properties_complete":technical_ok,
        "selection_score":score,
        "recalculation_required_if_substituted":True,
    }
    return normalized,None

def build_local_material_supply_context(
    *,
    repository: Path,
    project_id: str,
    architectural_model: dict[str,Any],
    structural_profile: dict[str,Any],
    project_context: dict[str,Any],
    manifest: dict[str,Any],
    as_of_date: str | date | None = None,
) -> MaterialSupplyResult:
    repository=repository.resolve()
    policy=_policy(repository)
    if isinstance(as_of_date,date):
        as_of=as_of_date
    elif as_of_date:
        as_of=_parse_date(as_of_date) or date.today()
    else:
        as_of=date.today()

    geography=_project_geo(project_context,manifest)
    requirements=derive_material_requirements(
        project_id=project_id,
        architectural_model=architectural_model,
        structural_profile=structural_profile,
    )
    blockers=[]
    warnings=[]
    if not geography["country_code"]:
        blockers.append({
            "reason":"PROJECT_LOCATION_REQUIRED_FOR_LOCAL_MATERIALS",
            "message":"Projectland/gebiedsdeel is vereist voordat lokale materiaal- en productbeschikbaarheid kan worden bevestigd.",
        })

    discovered,source_failures=_discover_catalogs(repository,policy)
    products=[]
    rejections=list(source_failures)
    if geography["country_code"]:
        for candidate in discovered:
            catalog=candidate["catalog"]
            rows=catalog.get("products")
            if not isinstance(rows,list):
                rejections.append({
                    "source_reference":candidate["source_reference"],
                    "reason":"MATERIAL_SUPPLY_PRODUCTS_ARRAY_REQUIRED",
                })
                continue
            for product in rows:
                if not isinstance(product,dict):
                    continue
                normalized,rejection=_product_record(
                    candidate=candidate,product=product,geography=geography,as_of=as_of,policy=policy
                )
                if normalized:
                    products.append(normalized)
                elif rejection:
                    rejections.append(rejection)

    selections=[]
    for req in requirements["requirements"]:
        family=req["material_family"]
        matches=[p for p in products if str(p.get("material_family") or "")==family]
        matches.sort(key=lambda x:x["selection_score"],reverse=True)

        confirmed=[
            p for p in matches
            if p["availability_status"]=="LOCAL_AVAILABILITY_CONFIRMED"
            and (not req["technical_properties_required"] or p["structural_technical_properties_complete"])
        ]
        selected=confirmed[0] if confirmed else None

        if selected:
            selections.append({
                "requirement_id":req["requirement_id"],
                "element_role":req["element_role"],
                "material_family":family,
                "selection_status":"LOCAL_AVAILABILITY_CONFIRMED",
                "selected_product":selected,
                "alternatives":[
                    {k:v for k,v in p.items() if k!="technical_properties"}
                    for p in confirmed[1:4]
                ],
                "substitution_policy":"RECALCULATION_AND_REVIEW_REQUIRED",
            })
            continue

        import_candidates=[
            p for p in matches
            if p["availability_status"] in {"REGIONAL_IMPORT_REQUIRED","INTERNATIONAL_IMPORT_REQUIRED"}
        ]
        probable=[
            p for p in matches
            if p["availability_status"]=="LOCAL_AVAILABILITY_PROBABLE"
        ]
        unavailable=[p for p in matches if p["availability_status"]=="UNAVAILABLE"]

        reason="LOCAL_MATERIAL_AVAILABILITY_REQUIRED"
        message=f"Geen lokaal bevestigde actuele productbeschikbaarheid gevonden voor materiaalcategorie {family}."
        status="AVAILABILITY_UNKNOWN"
        candidates=[]
        if probable:
            status="LOCAL_AVAILABILITY_PROBABLE"
            candidates=probable[:3]
            reason="LOCAL_MATERIAL_AVAILABILITY_CONFIRMATION_REQUIRED"
            message=f"Lokale beschikbaarheid voor {family} is slechts waarschijnlijk; actuele bevestiging is vereist."
        elif import_candidates:
            status=import_candidates[0]["availability_status"]
            candidates=import_candidates[:3]
            reason="LOCAL_MATERIAL_REQUIRED_IMPORT_CANDIDATE_ONLY"
            message=f"Voor {family} is alleen een importkandidaat gevonden; import wordt niet automatisch als lokaal geaccepteerd."
        elif unavailable:
            status="UNAVAILABLE"
            candidates=unavailable[:3]
            reason="LOCAL_MATERIAL_UNAVAILABLE"
            message=f"Lokale bron meldt {family} als niet beschikbaar."

        selections.append({
            "requirement_id":req["requirement_id"],
            "element_role":req["element_role"],
            "material_family":family,
            "selection_status":status,
            "selected_product":None,
            "candidates":[{k:v for k,v in p.items() if k!="technical_properties"} for p in candidates],
            "substitution_policy":"RECALCULATION_AND_REVIEW_REQUIRED",
        })
        blockers.append({
            "reason":reason,
            "requirement_id":req["requirement_id"],
            "material_family":family,
            "message":message,
        })

    all_confirmed=bool(requirements["requirements"]) and all(
        x["selection_status"]=="LOCAL_AVAILABILITY_CONFIRMED" for x in selections
    )
    structural_confirmed=all(
        any(
            s["requirement_id"]==req["requirement_id"]
            and s["selection_status"]=="LOCAL_AVAILABILITY_CONFIRMED"
            for s in selections
        )
        for req in requirements["requirements"] if req["structural"]
    )

    status="PASSED" if geography["country_code"] and all_confirmed else "BLOCKED"
    selection_register={
        "schema_version":"phoenix.local-material-selection-register/1.0",
        "engine_version":VERSION,
        "project_id":project_id,
        "as_of_date":as_of.isoformat(),
        "geography":geography,
        "selection_hierarchy":["CITY","REGION","COUNTRY","REGIONAL_IMPORT","INTERNATIONAL_IMPORT"],
        "local_means":["CITY","REGION","COUNTRY"],
        "status":status,
        "all_requirements_locally_confirmed":all_confirmed,
        "all_structural_requirements_locally_confirmed":structural_confirmed,
        "selections":selections,
        "automatic_import_approval":False,
        "automatic_product_substitution":False,
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    supply_register={
        "schema_version":"phoenix.local-material-supply-source-register/1.0",
        "project_id":project_id,
        "as_of_date":as_of.isoformat(),
        "catalog_count":len(discovered),
        "candidate_product_count":len(products),
        "sources":[
            {
                "source_id":x["source_id"],
                "source_kind":x["source_kind"],
                "source_reference":x["source_reference"],
                "source_priority":x["source_priority"],
            } for x in discovered
        ],
        "rejections":rejections,
        "source_evidence_required":True,
        "production_release":"LOCKED",
    }
    change_control={
        "schema_version":"phoenix.material-product-change-control/1.0",
        "project_id":project_id,
        "rule":"Any selected material/product substitution invalidates affected engineering and cost evidence until recalculated/reviewed.",
        "substitution_requires":{
            "digital_twin_update":True,
            "structural_recalculation_if_structural":True,
            "cost_recalculation":True,
            "planning_recalculation_if_lead_time_changes":True,
            "drawing_specification_update":True,
            "qaqc_recheck":True,
            "human_review":True,
        },
        "automatic_substitution":False,
        "production_release":"LOCKED",
    }
    return MaterialSupplyResult(
        status,requirements,selection_register,supply_register,change_control,blockers,warnings
    )

def selected_engineering_material_ids(selection_register: dict[str,Any]) -> set[str]:
    result=set()
    for item in selection_register.get("selections",[]):
        if not isinstance(item,dict):
            continue
        product=item.get("selected_product")
        if isinstance(product,dict) and product.get("engineering_material_id"):
            result.add(str(product["engineering_material_id"]))
    return result
