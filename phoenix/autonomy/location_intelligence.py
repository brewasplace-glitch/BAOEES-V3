"""Phoenix Project Location & Jurisdiction Intelligence v1.0.

Resolves only explicit project-location evidence or exact known-locality catalog
matches. UI locale is never used as project geography. No cadastral, legal,
planning or professional conclusion is invented.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .local_cost_intelligence import currency_for_country

VERSION = "1.0.0"

LOCALITIES = {
    "amsterdam":{"country_code":"NL","municipality":"Amsterdam","region_name":"Noord-Holland"},
    "rotterdam":{"country_code":"NL","municipality":"Rotterdam","region_name":"Zuid-Holland"},
    "den haag":{"country_code":"NL","municipality":"Den Haag","region_name":"Zuid-Holland"},
    "utrecht":{"country_code":"NL","municipality":"Utrecht","region_name":"Utrecht"},
    "bunschoten":{"country_code":"NL","municipality":"Bunschoten","region_name":"Utrecht"},
    "bunschoten-spakenburg":{"country_code":"NL","municipality":"Bunschoten","region_name":"Utrecht"},
    "paramaribo":{"country_code":"SR","municipality":"Paramaribo","region_name":"Paramaribo"},
    "wanica":{"country_code":"SR","municipality":"Wanica","region_name":"Wanica"},
    "nieuw nickerie":{"country_code":"SR","municipality":"Nieuw Nickerie","region_name":"Nickerie"},
    "willemstad":{"country_code":"CW","municipality":"Willemstad","region_name":"Curaçao"},
    "oranjestad":{"country_code":"AW","municipality":"Oranjestad","region_name":"Aruba"},
    "kralendijk":{"country_code":"BQ","municipality":"Kralendijk","region_name":"Bonaire"},
    "philipsburg":{"country_code":"SX","municipality":"Philipsburg","region_name":"Sint Maarten"},
    "georgetown":{"country_code":"GY","municipality":"Georgetown","region_name":"Demerara-Mahaica"},
}

COUNTRY_NAMES = {
    "NL":"Nederland","SR":"Suriname","BE":"België","DE":"Duitsland","FR":"Frankrijk",
    "US":"Verenigde Staten","GB":"Verenigd Koninkrijk","AW":"Aruba","CW":"Curaçao",
    "SX":"Sint Maarten","BQ":"Caribisch Nederland","GF":"Frans-Guyana","GY":"Guyana",
    "BR":"Brazilië","TT":"Trinidad en Tobago",
}

@dataclass
class LocationIntelligenceResult:
    status: str
    record: dict[str, Any]
    fact_updates: dict[str, Any]
    manifest_updates: dict[str, Any]
    blockers: list[dict[str, Any]]
    warnings: list[str]

def _norm(value: Any) -> str:
    return re.sub(r"\s+"," ",str(value or "").strip().casefold())

def _explicit_location(brief: str, manifest: dict[str,Any], context: dict[str,Any]) -> tuple[str|None,str]:
    facts=(context.get("facts") or {}) if isinstance(context,dict) else {}
    for value,basis in (
        (facts.get("project_location"),facts.get("project_location_basis") or "PROJECT_CONTEXT"),
        (manifest.get("location"),"PROJECT_MANIFEST"),
        (manifest.get("project_location"),"PROJECT_MANIFEST"),
    ):
        if isinstance(value,str) and value.strip():
            return value.strip(),str(basis)
    for line in str(brief or "").splitlines():
        m=re.match(r"(?i)^\s*(?:projectlocatie|locatie|adres|plaats|site)\s*[:=-]\s*(.+?)\s*$",line)
        if m and m.group(1).strip():
            return m.group(1).strip(),"EXPLICIT_BRIEF"
    return None,"MISSING"

def _explicit_coordinates(brief: str, manifest: dict[str,Any]) -> tuple[dict[str,float]|None,str]:
    for source in (manifest,):
        lat=source.get("latitude")
        lon=source.get("longitude")
        try:
            if lat is not None and lon is not None:
                return {"latitude":float(lat),"longitude":float(lon)},"PROJECT_MANIFEST"
        except (TypeError,ValueError):
            pass
    text=str(brief or "")
    patterns=[
        r"(?i)\b(?:co[oö]rdinaten|coordinates|gps)\s*[:=-]\s*(-?\d{1,2}(?:[.,]\d+)?)\s*[,;/ ]+\s*(-?\d{1,3}(?:[.,]\d+)?)",
        r"(?i)\blat(?:itude)?\s*[:=-]\s*(-?\d{1,2}(?:[.,]\d+)?)\D+lon(?:gitude)?\s*[:=-]\s*(-?\d{1,3}(?:[.,]\d+)?)",
    ]
    for pattern in patterns:
        m=re.search(pattern,text)
        if not m: continue
        lat=float(m.group(1).replace(",","."))
        lon=float(m.group(2).replace(",","."))
        if -90<=lat<=90 and -180<=lon<=180:
            return {"latitude":lat,"longitude":lon},"EXPLICIT_BRIEF"
    return None,"MISSING"

def _catalog_locality(location: str|None) -> tuple[dict[str,Any]|None,str]:
    if not location:
        return None,"MISSING"
    low=_norm(location)
    matches=[]
    for token,value in LOCALITIES.items():
        if re.search(r"(?<!\w)"+re.escape(token)+r"(?!\w)",low):
            matches.append((len(token),value,token))
    if not matches:
        return None,"MISSING"
    matches.sort(key=lambda x:x[0],reverse=True)
    _,value,token=matches[0]
    return dict(value),"KNOWN_LOCALITY_CATALOG:"+token

def resolve_location_intelligence(
    *,
    repository: Path,
    project_id: str,
    brief: str,
    manifest: dict[str,Any],
    project_context: dict[str,Any],
) -> LocationIntelligenceResult:
    location,location_basis=_explicit_location(brief,manifest,project_context)
    coords,coords_basis=_explicit_coordinates(brief,manifest)
    facts=(project_context.get("facts") or {}) if isinstance(project_context,dict) else {}

    explicit_country=str(facts.get("country_code") or manifest.get("country_code") or "").upper().strip() or None
    explicit_region=facts.get("region") or manifest.get("region")
    explicit_municipality=facts.get("municipality") or manifest.get("municipality")

    locality,locality_basis=_catalog_locality(location)
    country=explicit_country or (locality or {}).get("country_code")
    municipality=explicit_municipality or (locality or {}).get("municipality")
    region=explicit_region or (locality or {}).get("region_name")

    country_basis=(
        str(facts.get("country_basis") or "PROJECT_CONTEXT")
        if explicit_country else
        (locality_basis if country else "MISSING")
    )
    municipality_basis="PROJECT_CONTEXT" if explicit_municipality else (locality_basis if municipality else "MISSING")
    region_basis="PROJECT_CONTEXT" if explicit_region else (locality_basis if region else "MISSING")

    currency=currency_for_country(repository,country) if country else None
    jurisdiction_parts=[x for x in (country,region,municipality) if x]
    jurisdiction_key=":".join(str(x) for x in jurisdiction_parts) if jurisdiction_parts else None

    blockers=[]
    warnings=[]
    if not location and not coords:
        blockers.append({
            "reason":"PROJECT_LOCATION_REQUIRED",
            "message":"Geen expliciete projectlocatie of coördinaten aangetroffen.",
        })
    if not country:
        blockers.append({
            "reason":"PROJECT_COUNTRY_JURISDICTION_REQUIRED",
            "message":"Projectland/gebiedsdeel kan niet betrouwbaar uit de projectspecifieke locatie-evidence worden vastgesteld.",
        })

    status="RESOLVED" if location and country else ("PARTIAL" if country or location or coords else "BLOCKED")
    record={
        "schema_version":"phoenix.location-intelligence/1.0",
        "engine_version":VERSION,
        "project_id":project_id,
        "status":status,
        "location":{
            "text":location,
            "basis":location_basis,
            "coordinates":coords,
            "coordinates_basis":coords_basis,
        },
        "jurisdiction":{
            "country_code":country,
            "country_name":COUNTRY_NAMES.get(country) if country else None,
            "country_basis":country_basis,
            "region_name":region,
            "region_basis":region_basis,
            "municipality":municipality,
            "municipality_basis":municipality_basis,
            "jurisdiction_key":jurisdiction_key,
            "planning_rules_validated":False,
            "permit_rules_validated":False,
        },
        "currency":{
            "code":currency,
            "basis":"CURRENCY_CATALOG_FROM_RESOLVED_COUNTRY" if currency else "UNRESOLVED",
        },
        "cadastral":{
            "parcel_boundary_resolved":False,
            "parcel_id_resolved":False,
            "automatic_cadastral_inference":False,
        },
        "geocoding":{
            "remote_geocoding_used":False,
            "ui_locale_used":False,
            "known_locality_catalog_used":bool(locality),
        },
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    fact_updates={
        "project_location":location,
        "project_location_basis":location_basis,
        "country_code":country,
        "country_basis":country_basis,
        "region":region,
        "region_basis":region_basis,
        "municipality":municipality,
        "municipality_status":"RESOLVED_CANDIDATE" if municipality else "MISSING",
        "jurisdiction_status":"RESOLVED_CANDIDATE" if country else "MISSING",
        "currency":currency,
        "currency_basis":"CURRENCY_CATALOG_FROM_RESOLVED_COUNTRY" if currency else "MISSING",
        "location_intelligence_status":status,
    }
    manifest_updates={
        "location_intelligence_status":status,
        "jurisdiction_key":jurisdiction_key,
    }
    if location: manifest_updates["location"]=location
    if country: manifest_updates["country_code"]=country
    if region: manifest_updates["region"]=region
    if municipality: manifest_updates["municipality"]=municipality
    if currency: manifest_updates["currency"]=currency
    if coords:
        manifest_updates["latitude"]=coords["latitude"]
        manifest_updates["longitude"]=coords["longitude"]

    return LocationIntelligenceResult(status,record,fact_updates,manifest_updates,blockers,warnings)
