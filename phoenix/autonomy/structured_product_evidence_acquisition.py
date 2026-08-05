from __future__ import annotations

import hashlib
import html
import json
import os
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from phoenix.autonomy.material_route_intelligence import decide_routes

VERSION = "1.0.0"
BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
USER_AGENT = "Project-Phoenix/3.0 StructuredEvidence/1.0"
MAX_PAGE_BYTES = 1_500_000
MAX_DOC_BYTES = 5_000_000
MAX_RESULTS_PER_QUERY = 8
MAX_FETCH_PER_REQUIREMENT = 8


@dataclass
class FetchEvidence:
    url: str
    final_url: str
    content_type: str
    status: str
    sha256: Optional[str]
    extracted_text: str
    links: List[Tuple[str, str]]
    error: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _json_read(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _json_write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_slug(value: str, limit: int = 80) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return (text[:limit] or "item").strip("_")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _recursive_project_id(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        if value.get("project_id"):
            return str(value["project_id"])
        for child in value.values():
            found = _recursive_project_id(child)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _recursive_project_id(child)
            if found:
                return found
    return None


def _infer_workspace(base_result: Any, args: Sequence[Any], kwargs: Dict[str, Any]) -> Optional[Path]:
    repo = _repo_root()
    paths: List[Path] = []
    for key in ("workspace", "project_workspace", "project_dir"):
        if kwargs.get(key):
            paths.append(Path(str(kwargs[key])))
    pid = _recursive_project_id(base_result) or _recursive_project_id(kwargs) or _recursive_project_id(args)
    if pid:
        paths.append(repo / "projects" / "runtime" / pid)
    for path in paths:
        if path.exists():
            return path

    runtime = repo / "projects" / "runtime"
    if runtime.exists():
        candidates = [p for p in runtime.iterdir() if p.is_dir()]
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return candidates[0]
    return None


def _provider_enabled() -> Tuple[bool, str]:
    registry = _repo_root() / "configs" / "phoenix" / "global_supplier_discovery_provider_registry_v1_0.json"
    data = _json_read(registry)
    for provider in data.get("providers", []):
        if not isinstance(provider, dict):
            continue
        if provider.get("provider_id") == "BRAVE_WEB_SEARCH_API" and bool(provider.get("enabled")):
            env_name = str(provider.get("api_key_env") or "PHOENIX_BRAVE_SEARCH_API_KEY")
            return bool(os.environ.get(env_name)), env_name
    return False, "PHOENIX_BRAVE_SEARCH_API_KEY"


def _load_selections(workspace: Path) -> List[Dict[str, Any]]:
    path = workspace / "results" / "session_adapters" / "architecture" / "structural_material_selection_register.json"
    data = _json_read(path)
    selections = data.get("selections", [])
    return [item for item in selections if isinstance(item, dict)] if isinstance(selections, list) else []


def _query_plan(selection: Dict[str, Any], route: Dict[str, Any]) -> List[Dict[str, str]]:
    family = str(selection.get("material_family") or "").lower()
    requirement_id = str(selection.get("requirement_id") or "UNKNOWN")
    selected = selection.get("selected_product") if isinstance(selection.get("selected_product"), dict) else {}
    supplier = str(selected.get("supplier_name") or "").strip()
    desc = str(selected.get("description") or "").strip()

    plan: List[Dict[str, str]] = []
    if family == "structural_concrete":
        terms = " ".join(x for x in [supplier, desc, "structural concrete ready mix technical data concrete class certificate Suriname"] if x)
        plan.append({"tier": "SURINAME_LOCAL_TECHNICAL_EVIDENCE", "query": terms})
        return plan

    if family == "masonry_unit":
        local_terms = " ".join(x for x in [supplier, desc, "masonry block technical data compressive strength declaration performance Suriname"] if x)
        plan.append({"tier": "SURINAME_LOCAL_TECHNICAL_EVIDENCE", "query": local_terms})
        plan.extend([
            {"tier": "NETHERLANDS", "query": "loadbearing masonry block EN 771 declaration of performance compressive strength supplier Netherlands"},
            {"tier": "BELGIUM", "query": "loadbearing masonry block EN 771 declaration of performance compressive strength supplier Belgium"},
            {"tier": "EU27", "query": "loadbearing masonry unit EN 771 DoP CE compressive strength supplier Europe"},
        ])
        return plan

    if family == "structural_timber":
        return [
            {"tier": "NETHERLANDS", "query": "C24 structural timber EN 338 EN 14081 declaration of performance CE supplier Netherlands"},
            {"tier": "BELGIUM", "query": "C24 structural timber EN 338 EN 14081 declaration of performance CE supplier Belgium"},
            {"tier": "EU27", "query": "C24 structural timber EN 338 EN 14081 DoP CE supplier Europe"},
            {"tier": "GLOBAL", "query": "C24 structural timber EN 338 certified supplier declaration performance"},
        ]

    if family == "reinforcement_steel":
        return [
            {"tier": "NETHERLANDS", "query": "B500B reinforcing steel EN 10080 certificate technical datasheet supplier Netherlands"},
            {"tier": "BELGIUM", "query": "B500B reinforcement steel EN 10080 certificate technical datasheet supplier Belgium"},
            {"tier": "EU27", "query": "B500B B500C reinforcing steel EN 10080 certificate supplier Europe"},
            {"tier": "GLOBAL", "query": "B500B reinforcing steel certified supplier EN 10080 mill certificate"},
        ]

    return [{"tier": "GLOBAL", "query": f"{family} certified technical datasheet supplier"}]


def _brave_search(query: str, api_key: str) -> Dict[str, Any]:
    from urllib.parse import urlencode

    params = urlencode({"q": query, "count": MAX_RESULTS_PER_QUERY, "safesearch": "moderate"})
    request = Request(
        f"{BRAVE_ENDPOINT}?{params}",
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": USER_AGENT,
        },
    )
    context = ssl.create_default_context()
    with urlopen(request, timeout=20, context=context) as response:
        raw = response.read(2_000_000)
    data = json.loads(raw.decode("utf-8", errors="replace"))
    return data if isinstance(data, dict) else {}


def _html_to_text(raw: bytes) -> Tuple[str, List[Tuple[str, str]]]:
    text = raw.decode("utf-8", errors="replace")
    links: List[Tuple[str, str]] = []
    for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, flags=re.I | re.S):
        href = html.unescape(match.group(1).strip())
        anchor = re.sub(r"<[^>]+>", " ", match.group(2))
        anchor = html.unescape(re.sub(r"\s+", " ", anchor)).strip()
        links.append((href, anchor[:240]))
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, links


def _pdf_to_text(raw: bytes) -> str:
    # Prefer PyMuPDF if available; fall back to pypdf. No OCR and no fabrication.
    try:
        import fitz  # type: ignore

        doc = fitz.open(stream=raw, filetype="pdf")
        parts = []
        for page in doc[:30]:
            parts.append(page.get_text("text"))
        return re.sub(r"\s+", " ", " ".join(parts)).strip()
    except Exception:
        pass
    try:
        from pypdf import PdfReader  # type: ignore
        import io

        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages[:30]:
            parts.append(page.extract_text() or "")
        return re.sub(r"\s+", " ", " ".join(parts)).strip()
    except Exception:
        return ""


def _fetch(url: str, limit: int = MAX_PAGE_BYTES) -> FetchEvidence:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return FetchEvidence(url, url, "", "BLOCKED", None, "", [], "UNSUPPORTED_URL_SCHEME")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*;q=0.8"})
    try:
        with urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raw = raw[:limit]
            ctype = str(response.headers.get("Content-Type") or "").lower()
            final_url = response.geturl()
        digest = hashlib.sha256(raw).hexdigest()
        if "pdf" in ctype or final_url.lower().endswith(".pdf") or raw[:4] == b"%PDF":
            text = _pdf_to_text(raw)
            return FetchEvidence(url, final_url, ctype, "ACQUIRED", digest, text, [])
        text, links = _html_to_text(raw)
        return FetchEvidence(url, final_url, ctype, "ACQUIRED", digest, text, links)
    except Exception as exc:
        return FetchEvidence(url, url, "", "FAILED", None, "", [], type(exc).__name__)


def _contexts(text: str, patterns: Sequence[str], width: int = 140) -> List[str]:
    out: List[str] = []
    lower = text.lower()
    for pattern in patterns:
        start = 0
        p = pattern.lower()
        while True:
            idx = lower.find(p, start)
            if idx < 0:
                break
            left = max(0, idx - width)
            right = min(len(text), idx + len(pattern) + width)
            snippet = re.sub(r"\s+", " ", text[left:right]).strip()
            if snippet and snippet not in out:
                out.append(snippet[:500])
            start = idx + len(pattern)
            if len(out) >= 8:
                return out
    return out


def _extract_price(text: str) -> Dict[str, Any]:
    patterns = [
        ("EUR", r"€\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)"),
        ("EUR", r"\bEUR\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)"),
        ("USD", r"\bUSD\s*\$?\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)"),
        ("USD", r"\$\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)"),
    ]
    for currency, pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            raw = match.group(1).replace(".", "").replace(",", ".") if "," in match.group(1) else match.group(1)
            try:
                return {"currency": currency, "unit_price": float(raw), "price_basis": "PAGE_TEXT_EXPLICIT"}
            except ValueError:
                continue
    return {"currency": None, "unit_price": None, "price_basis": "NOT_ESTABLISHED"}


def _technical_eval(family: str, texts: Sequence[str]) -> Dict[str, Any]:
    text = " ".join(t for t in texts if t)
    lower = text.lower()
    result: Dict[str, Any] = {
        "technical_properties_complete": False,
        "engineering_qualified": False,
        "standards": [],
        "certification_evidence": [],
        "technical_properties": {},
        "evidence_contexts": [],
    }

    if family == "structural_timber":
        class_match = re.search(r"\b(C(?:14|16|18|20|22|24|27|30|35|40|45|50))\b", text, flags=re.I)
        standards = re.findall(r"\bEN\s*(338|14081(?:-1)?)\b", text, flags=re.I)
        doc = any(token in lower for token in ("declaration of performance", "\bdop\b", "ce marking", "ce-mark"))
        # literal \bdop\b above is intentionally backed up by regex below
        doc = doc or bool(re.search(r"\bDoP\b", text, flags=re.I))
        if class_match:
            result["technical_properties"]["strength_class"] = class_match.group(1).upper()
        result["standards"] = sorted({"EN " + s.upper() for s in standards})
        if doc:
            result["certification_evidence"].append("DOP_OR_CE_REFERENCE_IN_ACQUIRED_SOURCE")
        complete = bool(class_match and standards and doc)
        result["technical_properties_complete"] = complete
        result["engineering_qualified"] = complete
        result["evidence_contexts"] = _contexts(text, ["C24", "EN 338", "EN 14081", "Declaration of Performance", "DoP", "CE"])
        return result

    if family == "reinforcement_steel":
        grade = re.search(r"\bB500[ABC]\b", text, flags=re.I)
        standards = re.findall(r"\b(?:EN\s*10080|BS\s*4449|DIN\s*488)\b", text, flags=re.I)
        cert = any(token in lower for token in ("mill certificate", "inspection certificate", "certificate 3.1", "declaration of performance", "ce marking"))
        if grade:
            result["technical_properties"]["reinforcement_grade"] = grade.group(0).upper()
        result["standards"] = sorted({re.sub(r"\s+", " ", s.upper()) for s in standards})
        if cert:
            result["certification_evidence"].append("CERTIFICATE_REFERENCE_IN_ACQUIRED_SOURCE")
        complete = bool(grade and standards and cert)
        result["technical_properties_complete"] = complete
        result["engineering_qualified"] = complete
        result["evidence_contexts"] = _contexts(text, ["B500B", "B500C", "EN 10080", "BS 4449", "mill certificate", "certificate 3.1"])
        return result

    if family == "masonry_unit":
        standard = re.search(r"\bEN\s*771(?:-\d+)?\b", text, flags=re.I)
        strength = re.search(r"(?:compressive strength|druksterkte)[^0-9]{0,25}([0-9]+(?:[.,][0-9]+)?)\s*(?:N/mm2|N/mm²|MPa)", text, flags=re.I)
        doc = bool(re.search(r"\b(?:declaration of performance|DoP|CE marking)\b", text, flags=re.I))
        if standard:
            result["standards"] = [re.sub(r"\s+", " ", standard.group(0).upper())]
        if strength:
            result["technical_properties"]["compressive_strength_mpa"] = float(strength.group(1).replace(",", "."))
        if doc:
            result["certification_evidence"].append("DOP_OR_CE_REFERENCE_IN_ACQUIRED_SOURCE")
        complete = bool(standard and strength and doc)
        result["technical_properties_complete"] = complete
        result["engineering_qualified"] = complete
        result["evidence_contexts"] = _contexts(text, ["EN 771", "compressive strength", "druksterkte", "Declaration of Performance", "DoP"])
        return result

    if family == "structural_concrete":
        concrete_class = re.search(r"\bC(?:12/15|16/20|20/25|25/30|30/37|32/40|35/45|40/50|45/55|50/60|55/67)\b", text, flags=re.I)
        standard = re.search(r"\bEN\s*206\b", text, flags=re.I)
        supplier_quality = bool(re.search(r"\b(?:quality control|quality certificate|certified|laboratory|batch|mix design)\b", text, flags=re.I))
        if concrete_class:
            result["technical_properties"]["concrete_class"] = concrete_class.group(0).upper()
        if standard:
            result["standards"] = [re.sub(r"\s+", " ", standard.group(0).upper())]
        if supplier_quality:
            result["certification_evidence"].append("SUPPLIER_QUALITY_REFERENCE_IN_ACQUIRED_SOURCE")
        complete = bool(concrete_class and standard and supplier_quality)
        result["technical_properties_complete"] = complete
        result["engineering_qualified"] = complete
        result["evidence_contexts"] = _contexts(text, ["EN 206", "C25/30", "C30/37", "quality", "laboratory", "mix design"])
        return result

    return result


def _commercial_availability(text: str) -> bool:
    return bool(re.search(r"\b(?:in stock|available|order|buy|quote|request a quote|op voorraad|bestellen|offerte)\b", text, flags=re.I))


def _country_for_tier(tier: str) -> Optional[str]:
    return {"NETHERLANDS": "NL", "BELGIUM": "BE", "SURINAME_LOCAL": "SR", "SURINAME_LOCAL_TECHNICAL_EVIDENCE": "SR"}.get(tier)


def _candidate_from_evidence(
    requirement_id: str,
    family: str,
    tier: str,
    search_result: Dict[str, Any],
    page: FetchEvidence,
    doc_evidence: List[FetchEvidence],
    technical: Dict[str, Any],
) -> Dict[str, Any]:
    title = str(search_result.get("title") or "").strip()
    description = str(search_result.get("description") or "").strip()
    url = str(search_result.get("url") or page.final_url or page.url)
    domain = urlparse(url).netloc.lower()
    combined = " ".join([page.extracted_text] + [doc.extracted_text for doc in doc_evidence])
    price = _extract_price(combined)
    availability = _commercial_availability(combined)
    country = _country_for_tier(tier)
    source_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    standards = technical.get("standards", [])
    material_id = None
    if technical.get("engineering_qualified"):
        if family == "structural_timber":
            material_id = f"TIMBER-{technical.get('technical_properties', {}).get('strength_class', 'QUALIFIED')}"
        elif family == "reinforcement_steel":
            material_id = f"REBAR-{technical.get('technical_properties', {}).get('reinforcement_grade', 'QUALIFIED')}"
        elif family == "masonry_unit":
            material_id = "MASONRY-EN771-QUALIFIED"
        elif family == "structural_concrete":
            material_id = f"CONCRETE-{technical.get('technical_properties', {}).get('concrete_class', 'QUALIFIED')}"

    return {
        "requirement_id": requirement_id,
        "product_id": f"STRUCTEVID-{family.upper()}-{source_hash}",
        "supplier_product_code": None,
        "manufacturer": None,
        "supplier_id": domain or "WEB-SOURCE",
        "supplier_name": domain or title or "Web source",
        "description": title or description,
        "material_family": family,
        "engineering_material_id": material_id,
        "technical_properties": technical.get("technical_properties", {}),
        "standards": standards,
        "certifications": technical.get("certification_evidence", []),
        "structural_technical_properties_complete": bool(technical.get("technical_properties_complete")),
        "engineering_qualification_status": "QUALIFIED_FROM_ACQUIRED_TECHNICAL_EVIDENCE" if technical.get("engineering_qualified") else "NOT_QUALIFIED",
        "unit": None,
        "availability_status": "IMPORT_AVAILABILITY_CONFIRMED" if availability and country != "SR" else ("LOCAL_AVAILABILITY_CONFIRMED" if availability and country == "SR" else "SUPPLIER_DISCOVERED"),
        "source_availability_status": "AVAILABLE_TO_ORDER" if availability else "DISCOVERED_NOT_COMMERCIAL_CONFIRMED",
        "commercial_availability_confirmed": availability,
        "market_scope": "CITY" if country == "SR" else "GLOBAL",
        "lead_time_days": None,
        "minimum_order_quantity": None,
        "country_code": country,
        "region_name": None,
        "city": None,
        "availability_verified_date": _today(),
        "availability_valid_until": None,
        "availability_age_days": 0,
        "freshness_basis": "LIVE_ACQUISITION",
        "availability_evidence_fresh": True,
        "currency": price.get("currency"),
        "unit_price": price.get("unit_price"),
        "price_date": _today() if price.get("unit_price") is not None else None,
        "price_valid_until": None,
        "price_basis": price.get("price_basis"),
        "source_name": title or domain,
        "source_url": url,
        "source_reference": None,
        "source_kind": "project_runtime_live_supplier_evidence",
        "confidence": "HIGH" if technical.get("engineering_qualified") else "MEDIUM",
        "evidence_sha256": [x.sha256 for x in [page] + doc_evidence if x.sha256],
        "evidence_urls": [x.final_url for x in [page] + doc_evidence if x.status == "ACQUIRED"],
        "evidence_contexts": technical.get("evidence_contexts", []),
        "search_tier": tier,
        "recalculation_required_if_substituted": True,
        "automatic_ordering": False,
        "professional_review_required": True,
    }


def _document_links(page: FetchEvidence) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for href, anchor in page.links:
        abs_url = urljoin(page.final_url or page.url, href)
        test = f"{anchor} {abs_url}".lower()
        if not abs_url.startswith(("http://", "https://")):
            continue
        if any(token in test for token in (".pdf", "dop", "declaration", "performance", "certificate", "certificaat", "datasheet", "technical", "tds", "productblad")):
            out.append((abs_url, anchor))
    unique = []
    seen = set()
    for item in out:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique[:3]


def _infer_container_key(material_supply_dir: Path) -> str:
    for path in sorted(material_supply_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:25]:
        data = _json_read(path)
        for key, value in data.items():
            if not isinstance(value, list) or not value:
                continue
            sample = next((x for x in value if isinstance(x, dict)), None)
            if sample and ("material_family" in sample or "product_id" in sample or "unit_price" in sample):
                return str(key)
    return "products"


def _write_candidate_catalog(workspace: Path, candidate: Dict[str, Any]) -> str:
    supply_dir = workspace / "sources" / "material_supply"
    supply_dir.mkdir(parents=True, exist_ok=True)
    key = _infer_container_key(supply_dir)
    filename = f"IMP_STRUCTURED_{_safe_slug(str(candidate.get('material_family')))}_{hashlib.sha256(str(candidate.get('source_url')).encode()).hexdigest()[:12]}.json"
    path = supply_dir / filename
    repo = _repo_root()
    ref = str(path.relative_to(repo)).replace("\\", "/") if path.is_relative_to(repo) else str(path)
    candidate = dict(candidate)
    candidate["source_reference"] = ref
    payload = {
        "schema_version": "phoenix.material-supply-structured-evidence/1.0",
        "engine_version": VERSION,
        "source_id": path.stem,
        "generated_at": _now_iso(),
        "acquisition_method": "BRAVE_DISCOVERY_PLUS_DIRECT_SOURCE_FETCH",
        "automatic_ordering": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
        # Single-product top-level fields maximize compatibility with loaders that accept one object per catalog.
        **{k: v for k, v in candidate.items() if k not in {key}},
        key: [candidate],
    }
    _json_write(path, payload)
    return ref


def _normalize_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    web = data.get("web") if isinstance(data.get("web"), dict) else {}
    results = web.get("results", []) if isinstance(web, dict) else []
    out = []
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            if url.startswith(("http://", "https://")):
                out.append({
                    "title": str(item.get("title") or ""),
                    "url": url,
                    "description": str(item.get("description") or ""),
                })
    return out


def _redacted_error(exc: Exception) -> str:
    return type(exc).__name__


def _adjust_blockers(base: Dict[str, Any], routes: List[Dict[str, Any]], candidates: List[Dict[str, Any]], acquired_any_source: bool) -> None:
    qualified_req = {str(c.get("requirement_id")) for c in candidates if c.get("engineering_qualification_status") == "QUALIFIED_FROM_ACQUIRED_TECHNICAL_EVIDENCE"}
    route_by_req = {str(r.get("requirement_id")): r for r in routes}
    blockers = base.get("blockers")
    if not isinstance(blockers, list):
        blockers = []
    new_blockers = []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            new_blockers.append(blocker)
            continue
        reason = blocker.get("reason")
        req = str(blocker.get("requirement_id") or "")
        if reason == "NO_STRUCTURED_GLOBAL_PRODUCT_EVIDENCE_ACQUIRED" and acquired_any_source:
            continue
        if reason == "GLOBAL_PRODUCT_CANDIDATE_REQUIRED" and req in qualified_req:
            continue
        if reason == "GLOBAL_PRODUCT_CANDIDATE_REQUIRED" and req in route_by_req:
            route = route_by_req[req]
            if route.get("primary_route") == "LOCAL_READY_MIX_TECHNICAL_QUALIFICATION":
                blocker = dict(blocker)
                blocker["legacy_reason"] = reason
                blocker["route_reason"] = "LOCAL_STRUCTURAL_CONCRETE_TECHNICAL_EVIDENCE_REQUIRED"
                blocker["global_ready_mix_import_search_skipped"] = True
        new_blockers.append(blocker)
    base["blockers"] = new_blockers
    base["blocker_count"] = len(new_blockers)
    if new_blockers:
        base["status"] = "BLOCKED"
    elif candidates:
        base["status"] = "PASSED"


def enhance_acquisition_result(base_result: Any, args: Sequence[Any] = (), kwargs: Optional[Dict[str, Any]] = None) -> Any:
    kwargs = kwargs or {}
    if not isinstance(base_result, dict):
        return base_result

    workspace = _infer_workspace(base_result, args, kwargs)
    if workspace is None:
        base_result["structured_product_evidence"] = {"status": "BLOCKED", "reason": "PROJECT_WORKSPACE_REQUIRED"}
        return base_result

    project_id = workspace.name
    import_dir = workspace / "sources" / "import_acquisition"
    audit_dir = import_dir / "search_audit"
    evidence_dir = import_dir / "fetched_evidence"
    audit_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    selections = _load_selections(workspace)
    routes = decide_routes(selections)
    route_map = {str(r.get("requirement_id")): r for r in routes}
    provider_ok, env_name = _provider_enabled()
    api_key = os.environ.get(env_name, "") if provider_ok else ""

    register: Dict[str, Any] = {
        "schema_version": "phoenix.structured-product-evidence-acquisition/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "generated_at": _now_iso(),
        "provider": "BRAVE_WEB_SEARCH_API",
        "provider_enabled": provider_ok,
        "credential_present": bool(api_key),
        "credential_value_persisted": False,
        "route_decisions": routes,
        "search_runs": [],
        "fetch_runs": [],
        "candidates": [],
        "written_catalogs": [],
        "automatic_ordering": False,
        "automatic_payment": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }

    if not provider_ok or not api_key:
        register["status"] = "BLOCKED"
        register["blockers"] = [{"reason": "ACTIVE_SUPPLIER_DISCOVERY_PROVIDER_CREDENTIAL_REQUIRED"}]
        _json_write(import_dir / "structured_product_evidence_acquisition_register.json", register)
        base_result["structured_product_evidence"] = {
            "status": "BLOCKED",
            "register": str(import_dir / "structured_product_evidence_acquisition_register.json"),
        }
        return base_result

    candidates: List[Dict[str, Any]] = []
    acquired_any_source = False
    supplier_provider_runs = []
    enrichment_provider_runs = []

    for selection in selections:
        requirement_id = str(selection.get("requirement_id") or "UNKNOWN")
        family = str(selection.get("material_family") or "unknown").lower()
        route = route_map.get(requirement_id, {})
        plan = _query_plan(selection, route)
        fetched_count = 0
        qualified_for_requirement = False

        for q_index, query_item in enumerate(plan):
            if qualified_for_requirement and family in {"structural_timber", "reinforcement_steel", "masonry_unit"}:
                break
            tier = query_item["tier"]
            query = query_item["query"]
            search_record = {
                "requirement_id": requirement_id,
                "material_family": family,
                "tier": tier,
                "query": query,
                "provider": "BRAVE_WEB_SEARCH_API",
                "started_at": _now_iso(),
            }
            try:
                data = _brave_search(query, api_key)
                results = _normalize_results(data)
                search_record["status"] = "ACQUIRED"
                search_record["result_count"] = len(results)
                search_record["results"] = results
                supplier_provider_runs.append({
                    "provider_id": "BRAVE_WEB_SEARCH_API",
                    "material_family": family,
                    "requirement_id": requirement_id,
                    "tier": tier,
                    "status": "ACQUIRED",
                    "result_count": len(results),
                    "error": None,
                })
                acquired_any_source = acquired_any_source or bool(results)
            except Exception as exc:
                results = []
                search_record["status"] = "FAILED"
                search_record["error"] = _redacted_error(exc)
                supplier_provider_runs.append({
                    "provider_id": "BRAVE_WEB_SEARCH_API",
                    "material_family": family,
                    "requirement_id": requirement_id,
                    "tier": tier,
                    "status": "FAILED",
                    "result_count": 0,
                    "error": _redacted_error(exc),
                })
            search_record["finished_at"] = _now_iso()
            register["search_runs"].append(search_record)
            audit_path = audit_dir / f"{_safe_slug(requirement_id)}_{q_index:02d}_{_safe_slug(tier)}.json"
            _json_write(audit_path, search_record)

            for r_index, search_result in enumerate(results):
                if fetched_count >= MAX_FETCH_PER_REQUIREMENT:
                    break
                fetched_count += 1
                page = _fetch(search_result["url"], MAX_PAGE_BYTES)
                fetch_record = {
                    "requirement_id": requirement_id,
                    "material_family": family,
                    "tier": tier,
                    "url": search_result["url"],
                    "status": page.status,
                    "final_url": page.final_url,
                    "content_type": page.content_type,
                    "sha256": page.sha256,
                    "error": page.error,
                }
                doc_evidence: List[FetchEvidence] = []
                if page.status == "ACQUIRED":
                    acquired_any_source = True
                    for doc_url, anchor in _document_links(page):
                        doc = _fetch(doc_url, MAX_DOC_BYTES)
                        doc_evidence.append(doc)
                        enrichment_provider_runs.append({
                            "provider_id": "DIRECT_HTTPS_FETCH",
                            "category": "TECHNICAL_DOCUMENT",
                            "material_family": family,
                            "requirement_id": requirement_id,
                            "url": doc_url,
                            "status": doc.status,
                            "error": doc.error,
                        })
                    technical = _technical_eval(family, [page.extracted_text] + [d.extracted_text for d in doc_evidence])
                    fetch_record["engineering_qualified"] = technical.get("engineering_qualified")
                    fetch_record["technical_properties_complete"] = technical.get("technical_properties_complete")
                    fetch_record["standards"] = technical.get("standards")
                    fetch_record["certification_evidence"] = technical.get("certification_evidence")
                    fetch_record["evidence_contexts"] = technical.get("evidence_contexts")
                    fetch_record["document_urls"] = [d.final_url for d in doc_evidence if d.status == "ACQUIRED"]
                    if technical.get("engineering_qualified"):
                        candidate = _candidate_from_evidence(requirement_id, family, tier, search_result, page, doc_evidence, technical)
                        ref = _write_candidate_catalog(workspace, candidate)
                        candidate["source_reference"] = ref
                        candidates.append(candidate)
                        register["written_catalogs"].append(ref)
                        qualified_for_requirement = True
                register["fetch_runs"].append(fetch_record)
                evidence_path = evidence_dir / f"{_safe_slug(requirement_id)}_{q_index:02d}_{r_index:02d}.json"
                _json_write(evidence_path, fetch_record)

            # concrete is intentionally local-only; no international fallback in this engine
            if family == "structural_concrete":
                break

    register["candidates"] = candidates
    register["candidate_count"] = len(candidates)
    register["discovered_enriched_candidate_count"] = len(candidates)
    register["supplier_provider_runs"] = supplier_provider_runs
    register["enrichment_provider_runs"] = enrichment_provider_runs
    register["status"] = "PASSED" if candidates else "BLOCKED"
    register["blockers"] = [] if candidates else [{"reason": "NO_ENGINEERING_QUALIFIED_STRUCTURED_PRODUCT_EVIDENCE_ACQUIRED"}]

    structured_path = import_dir / "structured_product_evidence_acquisition_register.json"
    _json_write(structured_path, register)

    compatibility = {
        "schema_version": "phoenix.global-import-evidence-acquisition/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "generated_at": _now_iso(),
        "status": register["status"],
        "supplier_provider_runs": supplier_provider_runs,
        "enrichment_provider_runs": enrichment_provider_runs,
        "candidate_count": len(candidates),
        "written_catalogs": register["written_catalogs"],
        "automatic_ordering": False,
        "automatic_payment": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    compatibility_path = import_dir / "global_import_evidence_acquisition_register.json"
    _json_write(compatibility_path, compatibility)

    base_result["structured_product_evidence_enabled"] = True
    base_result["structured_product_evidence_register"] = str(structured_path.relative_to(_repo_root())).replace("\\", "/") if structured_path.is_relative_to(_repo_root()) else str(structured_path)
    base_result["global_import_evidence_acquisition_register"] = str(compatibility_path.relative_to(_repo_root())).replace("\\", "/") if compatibility_path.is_relative_to(_repo_root()) else str(compatibility_path)
    base_result["discovered_enriched_candidate_count"] = len(candidates)
    base_result["route_decisions"] = routes
    base_result["automatic_ordering"] = False
    base_result["automatic_payment"] = False
    base_result["professional_review_required"] = True
    base_result["production_release"] = "LOCKED"
    _adjust_blockers(base_result, routes, candidates, acquired_any_source)

    # Persist the enhanced compatibility register if the original engine already uses this path.
    original_register = import_dir / "global_supplier_import_acquisition_register.json"
    if original_register.exists():
        persisted = _json_read(original_register)
        if persisted:
            persisted.update({
                "structured_product_evidence_enabled": True,
                "structured_product_evidence_register": base_result.get("structured_product_evidence_register"),
                "global_import_evidence_acquisition_register": base_result.get("global_import_evidence_acquisition_register"),
                "discovered_enriched_candidate_count": len(candidates),
                "route_decisions": routes,
                "automatic_ordering": False,
                "automatic_payment": False,
                "professional_review_required": True,
                "production_release": "LOCKED",
            })
            # Apply the same conservative blocker transformation to the persisted view.
            persisted.setdefault("blockers", base_result.get("blockers", []))
            _adjust_blockers(persisted, routes, candidates, acquired_any_source)
            _json_write(original_register, persisted)

    return base_result
