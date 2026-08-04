"""Phoenix Local Cost Intelligence, Currency & Market Pricing Engine v1.0.

Hard rules:
- Project currency follows explicit project geography, never UI locale.
- Local/regional current price data is preferred over country-wide data.
- International/FX fallback is disabled by default and never silent.
- Every accepted ratebook must carry source, geography, currency and date evidence.
- Stale or mismatched price data blocks the cost gate instead of being treated as current.
- Taxes/levies are never invented when the source/jurisdiction does not define them.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

VERSION = "1.0.0"

DEFAULT_CURRENCIES = {
    "NL":"EUR","BE":"EUR","DE":"EUR","FR":"EUR","ES":"EUR","PT":"EUR","IT":"EUR",
    "IE":"EUR","LU":"EUR","AT":"EUR","FI":"EUR","GR":"EUR","CY":"EUR","MT":"EUR",
    "EE":"EUR","LV":"EUR","LT":"EUR","SK":"EUR","SI":"EUR","HR":"EUR",
    "SR":"SRD","US":"USD","GB":"GBP","GY":"GYD","BR":"BRL","TT":"TTD","BB":"BBD",
    "JM":"JMD","BS":"BSD","DO":"DOP","AW":"AWG","CW":"XCG","SX":"XCG","BQ":"USD",
    "GF":"EUR","CA":"CAD","MX":"MXN","CH":"CHF","NO":"NOK","SE":"SEK","DK":"DKK",
    "PL":"PLN","CZ":"CZK","HU":"HUF","RO":"RON","BG":"EUR","TR":"TRY","AE":"AED",
    "SA":"SAR","ZA":"ZAR","IN":"INR","CN":"CNY","JP":"JPY","SG":"SGD","AU":"AUD",
    "NZ":"NZD","ID":"IDR","MY":"MYR","TH":"THB","PH":"PHP","KR":"KRW",
}

@dataclass
class MarketContextResult:
    status: str
    market_context: dict[str, Any]
    source_register: dict[str, Any]
    selected_ratebooks: list[dict[str, Any]]
    blockers: list[dict[str, Any]]
    warnings: list[str]

def _read_json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value

def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text=str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None

def _norm(value: Any) -> str:
    text=str(value or "").strip().casefold()
    return re.sub(r"[^a-z0-9]+","",text)

def _load_policy(repository: Path) -> dict[str, Any]:
    path=repository/"configs"/"phoenix"/"local_cost_intelligence_policy_v1_0.json"
    if path.is_file():
        return _read_json(path)
    return {
        "freshness":{"default_max_age_days":90},
        "fx":{"international_reference_fallback_allowed":False},
        "remote":{"timeout_seconds":8,"maximum_bytes":5_000_000},
    }

def _load_currency_catalog(repository: Path) -> dict[str,str]:
    result=dict(DEFAULT_CURRENCIES)
    path=repository/"configs"/"phoenix"/"currency_jurisdiction_catalog_v1_0.json"
    if not path.is_file():
        return result
    value=_read_json(path)
    for item in value.get("jurisdictions",[]):
        if not isinstance(item,dict):
            continue
        code=str(item.get("country_code") or "").upper().strip()
        currency=str(item.get("currency_code") or "").upper().strip()
        if code and currency:
            result[code]=currency
    return result

def currency_for_country(repository: Path, country_code: str | None) -> str | None:
    code=str(country_code or "").upper().strip()
    if not code:
        return None
    return _load_currency_catalog(repository).get(code)

def _project_geography(project_context: dict[str,Any], manifest: dict[str,Any]) -> dict[str,Any]:
    facts=project_context.get("facts") if isinstance(project_context,dict) else {}
    facts=facts if isinstance(facts,dict) else {}
    country=str(facts.get("country_code") or manifest.get("country_code") or "").upper().strip() or None
    region=facts.get("region") or facts.get("region_name") or manifest.get("region") or manifest.get("region_name")
    municipality=facts.get("municipality") or manifest.get("municipality")
    location=facts.get("project_location") or manifest.get("location") or manifest.get("project_location")
    currency=str(facts.get("currency") or manifest.get("currency") or "").upper().strip() or None
    return {
        "country_code":country,
        "region_name":str(region).strip() if region else None,
        "municipality":str(municipality).strip() if municipality else None,
        "location":str(location).strip() if location else None,
        "currency":currency,
    }

def _registry(repository: Path) -> dict[str,Any]:
    path=repository/"configs"/"phoenix"/"market_price_source_registry_v1_0.json"
    if path.is_file():
        return _read_json(path)
    return {"sources":[]}

def _load_remote_json(url: str, timeout: float, maximum_bytes: int) -> dict[str,Any]:
    if not url.lower().startswith("https://"):
        raise ValueError("Only HTTPS remote market price sources are allowed.")
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Phoenix-Cost-Intelligence/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        raw=response.read(maximum_bytes+1)
    if len(raw)>maximum_bytes:
        raise ValueError("Remote market price source exceeds configured maximum size.")
    value=json.loads(raw.decode("utf-8"))
    if not isinstance(value,dict):
        raise ValueError("Remote market price source JSON root must be an object.")
    return value

def _discover_ratebooks(repository: Path, policy: dict[str,Any], project_id: str | None = None) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    registry=_registry(repository)
    discovered=[]
    failures=[]
    if project_id:
        runtime_root=repository/"projects"/"runtime"/project_id/"sources"/"market_prices"
        if runtime_root.is_dir():
            for path in sorted(runtime_root.rglob("*.json")):
                try:
                    discovered.append({
                        "source_id":"PROJECT_RUNTIME_MARKET_PRICES",
                        "source_kind":"project_runtime",
                        "source_priority":1000,
                        "source_max_age_days":90,
                        "source_reference":path.relative_to(repository).as_posix(),
                        "ratebook":_read_json(path),
                    })
                except Exception as exc:
                    failures.append({
                        "source_id":"PROJECT_RUNTIME_MARKET_PRICES",
                        "reference":str(path),
                        "reason":"INVALID_RATEBOOK_JSON",
                        "message":str(exc),
                    })
    remote_cfg=policy.get("remote") or {}
    timeout=float(remote_cfg.get("timeout_seconds",8))
    maximum_bytes=int(remote_cfg.get("maximum_bytes",5_000_000))
    for source in registry.get("sources",[]):
        if not isinstance(source,dict) or not source.get("enabled",False):
            continue
        source_id=str(source.get("source_id") or "UNNAMED")
        kind=str(source.get("kind") or "").lower()
        priority=int(source.get("priority",0))
        max_age_days=source.get("max_age_days")
        try:
            if kind=="filesystem_glob":
                pattern=str(source.get("glob") or "")
                for path in sorted(repository.glob(pattern)):
                    if not path.is_file() or path.suffix.lower()!=".json":
                        continue
                    try:
                        value=_read_json(path)
                        discovered.append({
                            "source_id":source_id,
                            "source_kind":kind,
                            "source_priority":priority,
                            "source_max_age_days":max_age_days,
                            "source_reference":path.relative_to(repository).as_posix(),
                            "ratebook":value,
                        })
                    except Exception as exc:
                        failures.append({"source_id":source_id,"reference":str(path),"reason":"INVALID_RATEBOOK_JSON","message":str(exc)})
            elif kind=="https_json":
                url=str(source.get("url") or "")
                value=_load_remote_json(url,timeout,maximum_bytes)
                discovered.append({
                    "source_id":source_id,
                    "source_kind":kind,
                    "source_priority":priority,
                    "source_max_age_days":max_age_days,
                    "source_reference":url,
                    "ratebook":value,
                })
            else:
                failures.append({"source_id":source_id,"reason":"UNSUPPORTED_SOURCE_KIND","message":kind})
        except Exception as exc:
            failures.append({"source_id":source_id,"reason":"SOURCE_FETCH_FAILED","message":str(exc)})
    return discovered,failures

def _metadata(ratebook: dict[str,Any]) -> dict[str,Any]:
    md=ratebook.get("metadata")
    return md if isinstance(md,dict) else ratebook

def _validate_ratebook(
    candidate: dict[str,Any],
    *,
    geography: dict[str,Any],
    project_currency: str,
    as_of: date,
    policy: dict[str,Any],
) -> tuple[bool,dict[str,Any]]:
    rb=candidate["ratebook"]
    md=_metadata(rb)
    rb_country=str(md.get("country_code") or "").upper().strip()
    rb_currency=str(md.get("currency") or md.get("currency_code") or "").upper().strip()
    rb_region=md.get("region_name") or md.get("region")
    rb_city=md.get("city") or md.get("municipality")
    effective=_parse_date(md.get("effective_date") or md.get("price_date") or md.get("source_date"))
    valid_until=_parse_date(md.get("valid_until"))
    prices=rb.get("prices")
    if not isinstance(prices,list) or not prices:
        return False,{"reason":"LOCAL_MARKET_PRICE_SOURCE_INVALID","detail":"prices array missing/empty"}

    if not rb_country:
        return False,{"reason":"LOCAL_MARKET_PRICE_SOURCE_INVALID","detail":"country_code missing"}
    if rb_country!=geography["country_code"]:
        return False,{"reason":"LOCAL_MARKET_PRICE_COUNTRY_MISMATCH","detail":f"{rb_country} != {geography['country_code']}"}
    if not rb_currency:
        return False,{"reason":"LOCAL_MARKET_PRICE_SOURCE_INVALID","detail":"currency missing"}
    if rb_currency!=project_currency:
        return False,{"reason":"LOCAL_MARKET_PRICE_CURRENCY_MISMATCH","detail":f"{rb_currency} != {project_currency}"}
    if not effective:
        return False,{"reason":"LOCAL_MARKET_PRICE_SOURCE_INVALID","detail":"effective_date missing/invalid"}
    if effective>as_of:
        return False,{"reason":"PRICE_DATA_EFFECTIVE_DATE_IN_FUTURE","detail":effective.isoformat()}

    default_age=int((policy.get("freshness") or {}).get("default_max_age_days",90))
    source_age=candidate.get("source_max_age_days")
    max_age=int(source_age) if source_age not in (None,"") else default_age
    age_days=(as_of-effective).days
    if valid_until is not None:
        if valid_until<as_of:
            return False,{"reason":"LOCAL_MARKET_PRICE_DATA_STALE","detail":f"valid_until={valid_until.isoformat()}"}
        freshness_basis="VALIDITY_WINDOW"
    elif age_days>max_age:
        return False,{"reason":"LOCAL_MARKET_PRICE_DATA_STALE","detail":f"age_days={age_days}, max={max_age}"}
    else:
        freshness_basis="AGE_LIMIT"

    score=int(candidate.get("source_priority",0))
    specificity="COUNTRY"
    project_region=geography.get("region_name")
    project_city=geography.get("municipality")
    if rb_region:
        if project_region and _norm(rb_region)==_norm(project_region):
            score+=1000
            specificity="REGION"
        elif project_region:
            return False,{"reason":"LOCAL_MARKET_PRICE_REGION_MISMATCH","detail":f"{rb_region} != {project_region}"}
        else:
            # A region-specific book may not be used as if it were national.
            return False,{"reason":"PROJECT_REGION_REQUIRED_FOR_REGIONAL_PRICEBOOK","detail":str(rb_region)}
    if rb_city:
        if project_city and _norm(rb_city)==_norm(project_city):
            score+=2000
            specificity="CITY"
        elif project_city:
            return False,{"reason":"LOCAL_MARKET_PRICE_CITY_MISMATCH","detail":f"{rb_city} != {project_city}"}
        else:
            return False,{"reason":"PROJECT_CITY_REQUIRED_FOR_CITY_PRICEBOOK","detail":str(rb_city)}

    score+=max(0,500-min(age_days,500))
    normalized={
        "ratebook_id":md.get("ratebook_id") or md.get("id") or candidate["source_id"],
        "title":md.get("title") or md.get("name") or candidate["source_id"],
        "country_code":rb_country,
        "region_name":rb_region,
        "city":rb_city,
        "currency":rb_currency,
        "effective_date":effective.isoformat(),
        "valid_until":valid_until.isoformat() if valid_until else None,
        "age_days":age_days,
        "freshness_basis":freshness_basis,
        "specificity":specificity,
        "source_name":md.get("source_name") or md.get("publisher") or candidate["source_id"],
        "source_url":md.get("source_url"),
        "source_reference":candidate["source_reference"],
        "source_kind":candidate["source_kind"],
        "confidence":str(md.get("confidence") or "MEDIUM").upper(),
        "taxes_included":md.get("taxes_included"),
        "transport_included":md.get("transport_included"),
        "source_priority":candidate.get("source_priority",0),
        "selection_score":score,
        "prices":prices,
    }
    return True,normalized

def build_local_cost_market_context(
    *,
    repository: Path,
    project_id: str,
    project_context: dict[str,Any],
    manifest: dict[str,Any],
    as_of_date: str | date | None = None,
) -> MarketContextResult:
    repository=repository.resolve()
    policy=_load_policy(repository)
    if isinstance(as_of_date,date):
        as_of=as_of_date
    elif as_of_date:
        as_of=_parse_date(as_of_date) or date.today()
    else:
        as_of=date.today()

    geography=_project_geography(project_context,manifest)
    blockers=[]
    warnings=[]

    if not geography["country_code"]:
        blockers.append({
            "reason":"PROJECT_COUNTRY_REQUIRED_FOR_LOCAL_COSTS",
            "message":"Projectland/gebiedsdeel ontbreekt; lokale valuta en lokale marktprijzen kunnen niet betrouwbaar worden bepaald.",
        })
        return MarketContextResult("BLOCKED",{
            "schema_version":"phoenix.local-cost-market-context/1.0","project_id":project_id,
            "as_of_date":as_of.isoformat(),"geography":geography,"pricing_gate":"BLOCKED",
        },{"sources":[],"rejections":[]},[],blockers,warnings)

    project_currency=geography["currency"] or currency_for_country(repository,geography["country_code"])
    if not project_currency:
        blockers.append({
            "reason":"LOCAL_CURRENCY_MAPPING_REQUIRED",
            "message":"Voor dit land/gebiedsdeel is nog geen lokale valuta in de Phoenix-valutacatalogus vastgelegd.",
            "country_code":geography["country_code"],
        })
        return MarketContextResult("BLOCKED",{
            "schema_version":"phoenix.local-cost-market-context/1.0","project_id":project_id,
            "as_of_date":as_of.isoformat(),"geography":geography,"pricing_gate":"BLOCKED",
        },{"sources":[],"rejections":[]},[],blockers,warnings)

    discovered,source_failures=_discover_ratebooks(repository,policy,project_id)
    accepted=[]
    rejections=list(source_failures)
    for candidate in discovered:
        ok,value=_validate_ratebook(
            candidate,geography=geography,project_currency=project_currency,as_of=as_of,policy=policy
        )
        if ok:
            accepted.append(value)
        else:
            rejections.append({
                "source_id":candidate["source_id"],
                "source_reference":candidate["source_reference"],
                **value,
            })

    accepted.sort(key=lambda x:(x["selection_score"],x["effective_date"]),reverse=True)
    max_selected=int((policy.get("selection") or {}).get("maximum_selected_ratebooks",3))
    selected=accepted[:max_selected]

    if not selected:
        reasons={str(x.get("reason") or "") for x in rejections}
        if "LOCAL_MARKET_PRICE_DATA_STALE" in reasons:
            reason="LOCAL_MARKET_PRICE_DATA_STALE"
            message="Beschikbare lokale prijsdata is niet meer actueel volgens de geldigheids-/freshnessregels."
        elif "LOCAL_MARKET_PRICE_CURRENCY_MISMATCH" in reasons:
            reason="LOCAL_MARKET_PRICE_CURRENCY_MISMATCH"
            message="Lokale prijsdata is beschikbaar, maar niet in de projectvaluta."
        else:
            reason="CURRENT_LOCAL_MARKET_PRICE_DATA_REQUIRED"
            message="Geen actuele lokale/regionale prijsbron gevonden voor projectland/gebiedsdeel en projectvaluta."
        blockers.append({"reason":reason,"message":message,"country_code":geography["country_code"],"currency":project_currency})
        context={
            "schema_version":"phoenix.local-cost-market-context/1.0",
            "engine_version":VERSION,
            "project_id":project_id,
            "as_of_date":as_of.isoformat(),
            "geography":{**geography,"currency":project_currency},
            "pricing_hierarchy":["CITY","REGION","COUNTRY"],
            "pricing_gate":"BLOCKED",
            "fx_fallback_allowed":bool((policy.get("fx") or {}).get("international_reference_fallback_allowed",False)),
            "automatic_tax_application":False,
            "production_release":"LOCKED",
        }
        return MarketContextResult("BLOCKED",context,{"sources":discovered,"rejections":rejections},[],blockers,warnings)

    best=selected[0]
    if best["specificity"]=="COUNTRY" and geography.get("region_name"):
        warnings.append("Geen actueel regionaal prijsboek gevonden; actueel landelijk prijsboek geselecteerd.")
    if best["confidence"]=="LOW":
        warnings.append("Geselecteerde marktprijsbron heeft lage bronbetrouwbaarheid.")

    tax_status="SOURCE_DECLARED" if best.get("taxes_included") is not None else "UNRESOLVED_NOT_APPLIED"
    context={
        "schema_version":"phoenix.local-cost-market-context/1.0",
        "engine_version":VERSION,
        "project_id":project_id,
        "as_of_date":as_of.isoformat(),
        "geography":{**geography,"currency":project_currency},
        "project_currency":project_currency,
        "selected_pricing_level":best["specificity"],
        "primary_ratebook":{k:v for k,v in best.items() if k!="prices"},
        "selected_ratebook_count":len(selected),
        "pricing_hierarchy":["CITY","REGION","COUNTRY"],
        "local_prices_required":True,
        "fx_used":False,
        "fx_fallback_allowed":bool((policy.get("fx") or {}).get("international_reference_fallback_allowed",False)),
        "tax_policy_status":tax_status,
        "automatic_tax_application":False,
        "pricing_gate":"PASSED",
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    source_register={
        "schema_version":"phoenix.local-cost-price-source-register/1.0",
        "project_id":project_id,
        "as_of_date":as_of.isoformat(),
        "selected":[{k:v for k,v in x.items() if k!="prices"} for x in selected],
        "rejections":rejections,
        "source_evidence_required":True,
        "production_release":"LOCKED",
    }
    return MarketContextResult("PASSED",context,source_register,selected,blockers,warnings)

def lookup_price(
    selected_ratebooks: list[dict[str,Any]],
    *,
    item_code: str | None = None,
    description: str | None = None,
    unit: str | None = None,
) -> dict[str,Any] | None:
    code=_norm(item_code)
    desc=_norm(description)
    unit_norm=_norm(unit)
    for rb in selected_ratebooks:
        for row in rb.get("prices",[]):
            if not isinstance(row,dict):
                continue
            row_code=_norm(row.get("item_code") or row.get("code"))
            row_desc=_norm(row.get("description"))
            row_unit=_norm(row.get("unit"))
            matched=bool(code and row_code==code) or bool(desc and row_desc==desc)
            if matched and (not unit_norm or unit_norm==row_unit):
                try:
                    unit_price=float(row.get("unit_price"))
                except (TypeError,ValueError):
                    continue
                return {
                    "item_code":row.get("item_code") or row.get("code"),
                    "description":row.get("description"),
                    "unit":row.get("unit"),
                    "unit_price":unit_price,
                    "currency":rb["currency"],
                    "components":row.get("components") if isinstance(row.get("components"),dict) else {},
                    "source_name":rb["source_name"],
                    "source_reference":rb["source_reference"],
                    "effective_date":rb["effective_date"],
                    "region_name":rb.get("region_name"),
                    "city":rb.get("city"),
                    "confidence":rb.get("confidence"),
                    "fx_used":False,
                }
    return None

def calculate_cost_items(
    *,
    quantity_items: list[dict[str,Any]],
    market_result: MarketContextResult,
) -> dict[str,Any]:
    if market_result.status!="PASSED":
        return {"status":"BLOCKED","items":[],"blockers":list(market_result.blockers)}
    items=[]
    blockers=[]
    currency=market_result.market_context["project_currency"]
    total=0.0
    for quantity in quantity_items:
        price=lookup_price(
            market_result.selected_ratebooks,
            item_code=quantity.get("item_code"),
            description=quantity.get("description"),
            unit=quantity.get("unit"),
        )
        if price is None:
            blockers.append({
                "reason":"QUANTITY_PRICE_MATCH_REQUIRED",
                "item_code":quantity.get("item_code"),
                "description":quantity.get("description"),
                "message":"Geen actuele lokale prijsregel gevonden voor deze hoeveelheid.",
            })
            continue
        try:
            qty=float(quantity.get("quantity"))
        except (TypeError,ValueError):
            blockers.append({"reason":"INVALID_QUANTITY","item_code":quantity.get("item_code")})
            continue
        line_total=round(qty*price["unit_price"],2)
        total+=line_total
        items.append({
            **quantity,
            "unit_price":price["unit_price"],
            "line_total":line_total,
            "currency":currency,
            "price_source":{
                "source_name":price["source_name"],
                "source_reference":price["source_reference"],
                "effective_date":price["effective_date"],
                "region_name":price["region_name"],
                "city":price["city"],
                "confidence":price["confidence"],
            },
            "components":price["components"],
            "fx_used":False,
        })
    return {
        "schema_version":"phoenix.local-cost-calculation/1.0",
        "status":"BLOCKED" if blockers else "PASSED",
        "currency":currency,
        "total":round(total,2),
        "items":items,
        "blockers":blockers,
        "automatic_tax_application":False,
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
