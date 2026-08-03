"""Phoenix Autonomous Real-World Data Acquisition Engine v1.0.

This engine acquires only explicitly configured or user-supplied real-world
sources. It never invents suppliers, prices, code values, cadastral facts, or
live availability. Remote sources are HTTPS-only and every acquisition is
registered with provenance and SHA256.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SUPPORTED_CATEGORIES = {
    "market_prices",
    "material_supply",
    "structural_action_load",
    "site_context",
}

@dataclass
class AcquisitionResult:
    status: str
    register: dict[str, Any]
    acquired_files: list[Path]
    blockers: list[dict[str, Any]]
    warnings: list[str]

def _read_json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value

def _registry(repository: Path) -> dict[str,Any]:
    path=repository/"configs"/"phoenix"/"real_world_data_source_registry_v1_0.json"
    if path.is_file():
        return _read_json(path)
    return {"providers":[]}

def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()

def _geo(project_context: dict[str,Any], manifest: dict[str,Any]) -> dict[str,Any]:
    facts=(project_context.get("facts") or {}) if isinstance(project_context,dict) else {}
    return {
        "country_code":str(facts.get("country_code") or manifest.get("country_code") or "").upper().strip() or None,
        "region_name":facts.get("region") or manifest.get("region"),
        "municipality":facts.get("municipality") or manifest.get("municipality"),
        "location":facts.get("project_location") or manifest.get("location"),
    }

def _provider_matches(provider: dict[str,Any], geography: dict[str,Any]) -> bool:
    countries=[str(x).upper() for x in provider.get("country_codes",[]) if str(x).strip()]
    if countries and geography.get("country_code") not in countries:
        return False
    regions=[_norm(x) for x in provider.get("regions",[]) if str(x).strip()]
    if regions and _norm(geography.get("region_name")) not in regions:
        return False
    cities=[_norm(x) for x in provider.get("municipalities",[]) if str(x).strip()]
    if cities and _norm(geography.get("municipality")) not in cities:
        return False
    return True

def _url(provider: dict[str,Any], geography: dict[str,Any], project_id: str) -> str:
    template=str(provider.get("url") or provider.get("url_template") or "").strip()
    values={
        "project_id":project_id,
        "country_code":geography.get("country_code") or "",
        "region":geography.get("region_name") or "",
        "municipality":geography.get("municipality") or "",
        "location":geography.get("location") or "",
    }
    try:
        return template.format(**values)
    except Exception:
        return template

def _fetch(url: str, *, timeout: float, maximum_bytes: int, response_type: str) -> tuple[bytes,Any]:
    if not url.lower().startswith("https://"):
        raise ValueError("Only HTTPS remote real-world sources are allowed.")
    request=urllib.request.Request(url,headers={"User-Agent":"Project-Phoenix-Real-World-Acquisition/1.0"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=response.read(maximum_bytes+1)
    if len(raw)>maximum_bytes:
        raise ValueError("Remote source exceeds configured maximum size.")
    if response_type=="json":
        parsed=json.loads(raw.decode("utf-8"))
    elif response_type=="csv":
        text=raw.decode("utf-8-sig")
        parsed={"rows":list(csv.DictReader(io.StringIO(text)))}
    else:
        raise ValueError(f"Unsupported response_type: {response_type}")
    if not isinstance(parsed,dict):
        raise ValueError("Remote real-world source must normalize to a JSON object.")
    return raw,parsed

def _destination(repository: Path, category: str, project_id: str) -> Path:
    mapping={
        "market_prices":repository/"inputs"/"market_prices"/"acquired"/project_id,
        "material_supply":repository/"inputs"/"material_supply"/"acquired"/project_id,
        "structural_action_load":repository/"inputs"/"structural_action_load"/"acquired"/project_id,
        "site_context":repository/"inputs"/"site_context"/"acquired"/project_id,
    }
    return mapping[category]

def _classify_uploaded_json(value: dict[str,Any]) -> str|None:
    schema=str(value.get("schema_version") or "").lower()
    if "real-world-source-manifest" in schema:
        return "source_manifest"
    if isinstance(value.get("prices"),list) or isinstance((value.get("ratebook") or {}).get("prices"),list):
        return "market_prices"
    if isinstance(value.get("products"),list):
        return "material_supply"
    if isinstance(value.get("action_load_input"),dict):
        return "structural_action_load"
    if value.get("type") in {"Feature","FeatureCollection"} or isinstance(value.get("site_context"),dict):
        return "site_context"
    return None

def _source_manifests(upload_paths: list[Path]) -> list[dict[str,Any]]:
    result=[]
    for path in upload_paths:
        if path.suffix.lower() not in {".json",".geojson"}:
            continue
        try:value=_read_json(path)
        except Exception:continue
        if _classify_uploaded_json(value)=="source_manifest":
            for item in value.get("sources",[]):
                if isinstance(item,dict):
                    result.append(item)
    return result

def acquire_real_world_data(
    *,
    repository: Path,
    project_id: str,
    project_context: dict[str,Any],
    manifest: dict[str,Any],
    upload_paths: list[Path],
) -> AcquisitionResult:
    repository=repository.resolve()
    geography=_geo(project_context,manifest)
    cfg=_registry(repository)
    remote_cfg=cfg.get("remote") or {}
    timeout=float(remote_cfg.get("timeout_seconds",8))
    maximum_bytes=int(remote_cfg.get("maximum_bytes",5_000_000))
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    acquired=[]
    entries=[]
    blockers=[]
    warnings=[]

    # Direct user-uploaded machine-readable evidence.
    for path in upload_paths:
        if path.suffix.lower() not in {".json",".geojson"}:
            continue
        try:value=_read_json(path)
        except Exception:continue
        category=_classify_uploaded_json(value)
        if category not in SUPPORTED_CATEGORIES:
            continue
        dest_dir=_destination(repository,category,project_id)
        dest_dir.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        dest=dest_dir/f"UPLOAD_{digest[:12]}_{path.name}"
        if path.resolve()!=dest.resolve():
            shutil.copy2(path,dest)
        acquired.append(dest)
        entries.append({
            "provider_id":"USER_UPLOAD",
            "category":category,
            "status":"ACQUIRED",
            "source_reference":str(path),
            "destination":dest.relative_to(repository).as_posix(),
            "sha256":digest,
            "acquired_at":now,
            "remote":False,
        })

    providers=[]
    providers.extend(x for x in cfg.get("providers",[]) if isinstance(x,dict))
    providers.extend(_source_manifests(upload_paths))

    for provider in providers:
        if not provider.get("enabled",True):
            continue
        category=str(provider.get("category") or "").strip()
        provider_id=str(provider.get("provider_id") or "UNNAMED")
        if category not in SUPPORTED_CATEGORIES:
            entries.append({"provider_id":provider_id,"status":"SKIPPED","reason":"UNSUPPORTED_CATEGORY"})
            continue
        if not _provider_matches(provider,geography):
            entries.append({"provider_id":provider_id,"category":category,"status":"SKIPPED","reason":"GEOGRAPHY_MISMATCH"})
            continue
        url=_url(provider,geography,project_id)
        if not url:
            entries.append({"provider_id":provider_id,"category":category,"status":"SKIPPED","reason":"URL_REQUIRED"})
            continue
        response_type=str(provider.get("response_type") or "json").lower()
        try:
            raw,value=_fetch(url,timeout=timeout,maximum_bytes=maximum_bytes,response_type=response_type)
            dest_dir=_destination(repository,category,project_id)
            dest_dir.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256(raw).hexdigest()
            dest=dest_dir/f"{provider_id}_{digest[:12]}.json"
            dest.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            acquired.append(dest)
            entries.append({
                "provider_id":provider_id,
                "category":category,
                "status":"ACQUIRED",
                "source_url":url,
                "destination":dest.relative_to(repository).as_posix(),
                "sha256":digest,
                "acquired_at":now,
                "remote":True,
            })
        except Exception as exc:
            entries.append({
                "provider_id":provider_id,
                "category":category,
                "status":"FAILED",
                "source_url":url,
                "reason":"ACQUISITION_FAILED",
                "message":str(exc),
            })
            warnings.append(f"Real-world provider {provider_id} kon niet worden opgehaald: {exc}")

    register={
        "schema_version":"phoenix.real-world-data-acquisition-register/1.0",
        "engine_version":VERSION,
        "project_id":project_id,
        "acquired_at":now,
        "geography":geography,
        "entries":entries,
        "acquired_count":sum(1 for x in entries if x.get("status")=="ACQUIRED"),
        "failed_count":sum(1 for x in entries if x.get("status")=="FAILED"),
        "web_search_used":False,
        "only_explicit_or_configured_sources":True,
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    return AcquisitionResult("PASSED",register,acquired,blockers,warnings)
