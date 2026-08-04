"""Phoenix Global Material Sourcing, Certification & Landed Cost Intelligence v1.0.

Local-first procurement intelligence for Project Phoenix. When a required material
is not locally available or is not technically engineering-qualified, this engine
may compare explicit project evidence and configured HTTPS supplier feeds. It only
selects candidates with traceable technical/certification evidence and complete
landed-cost evidence to the project destination. It never places orders, invents
certificates, customs rates, freight, taxes, FX rates or availability.
"""
from __future__ import annotations

import json
import math
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
STRUCTURAL_FAMILIES = {
    "masonry_unit", "structural_concrete", "reinforcement_steel",
    "structural_timber", "structural_steel_section",
}
AVAILABLE = {"AVAILABLE", "AVAILABLE_TO_ORDER", "IN_STOCK", "LOCAL_AVAILABILITY_CONFIRMED"}

@dataclass
class GlobalMaterialSourcingResult:
    status: str
    sourcing_register: dict[str, Any]
    candidate_comparison: dict[str, Any]
    landed_cost_register: dict[str, Any]
    structural_selection_register: dict[str, Any]
    blockers: list[dict[str, Any]]
    warnings: list[str]


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _project_currency(project_context: dict[str, Any], manifest: dict[str, Any]) -> str | None:
    facts = project_context.get("facts") if isinstance(project_context, dict) else {}
    facts = facts if isinstance(facts, dict) else {}
    value = facts.get("currency") or manifest.get("currency")
    return str(value).upper().strip() if value else None


def _destination(project_context: dict[str, Any]) -> dict[str, Any]:
    facts = project_context.get("facts") if isinstance(project_context, dict) else {}
    facts = facts if isinstance(facts, dict) else {}
    return {
        "country_code": str(facts.get("country_code") or "").upper() or None,
        "region": facts.get("region") or facts.get("region_name"),
        "city": facts.get("municipality") or facts.get("city"),
        "location": facts.get("project_location") or facts.get("location"),
    }


def _is_structural_requirement(item: dict[str, Any]) -> bool:
    fam = str(item.get("material_family") or "")
    role = str(item.get("element_role") or "")
    return fam in STRUCTURAL_FAMILIES or role in {
        "loadbearing_wall", "column", "slab", "beam", "roof_structure", "reinforcement",
    }


def _certified(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    certs = candidate.get("certifications")
    if not isinstance(certs, list) or not certs:
        return False, ["CERTIFICATION_EVIDENCE_REQUIRED"]
    valid = False
    for cert in certs:
        if isinstance(cert, str) and cert.strip():
            valid = True
            continue
        if isinstance(cert, dict):
            standard = cert.get("standard") or cert.get("scheme")
            evidence = cert.get("evidence_url") or cert.get("source_reference") or cert.get("certificate_id")
            if standard and evidence:
                valid = True
    return (True, []) if valid else (False, ["CERTIFICATION_REFERENCE_INCOMPLETE"])


def _freshness(candidate: dict[str, Any], policy: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    checks = [
        (candidate.get("availability_verified_date"), int(policy.get("availability_max_age_days", 30)), "CURRENT_AVAILABILITY_EVIDENCE_REQUIRED"),
        (candidate.get("price_date"), int(policy.get("price_max_age_days", 30)), "CURRENT_PRODUCT_PRICE_EVIDENCE_REQUIRED"),
    ]
    logistics = candidate.get("logistics") if isinstance(candidate.get("logistics"), dict) else {}
    freight_date = candidate.get("freight_quote_date") or logistics.get("quote_date") or logistics.get("freight_quote_date")
    if freight_date:
        checks.append((freight_date, int(policy.get("freight_max_age_days", 14)), "CURRENT_FREIGHT_QUOTE_REQUIRED"))
    for value, max_age, reason in checks:
        if value:
            age = _date_age_days(value)
            if age is None or age > max_age:
                reasons.append(reason)
    for cert in candidate.get("certifications") or []:
        if isinstance(cert, dict) and cert.get("valid_until"):
            try:
                if date.fromisoformat(str(cert["valid_until"])[:10]) < date.today():
                    reasons.append("CERTIFICATION_EXPIRED")
            except Exception:
                reasons.append("CERTIFICATION_VALIDITY_UNREADABLE")
    return not reasons, reasons


def _engineering_qualified(candidate: dict[str, Any], family: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    eng = str(candidate.get("engineering_material_id") or "").strip()
    tech = candidate.get("technical_properties")
    tech = tech if isinstance(tech, dict) else {}
    text = " ".join(str(v) for v in tech.values()) + " " + str(candidate.get("description") or "")
    if not eng:
        reasons.append("ENGINEERING_MATERIAL_ID_REQUIRED")
    if family == "reinforcement_steel":
        if not (tech.get("declared_reinforcement_grade") or tech.get("yield_strength_mpa") or "B500" in text.upper() or "FEB400" in text.upper()):
            reasons.append("REINFORCEMENT_GRADE_OR_YIELD_STRENGTH_REQUIRED")
    elif family == "structural_timber":
        if not (tech.get("declared_timber_strength_class") or tech.get("strength_class") or any(x in text.upper() for x in ("C18","C24","C30","C35","C40"))):
            reasons.append("TIMBER_STRENGTH_CLASS_REQUIRED")
    elif family == "structural_concrete":
        if not (tech.get("declared_concrete_strength_class") or tech.get("strength_class") or eng.startswith("CONCRETE_")):
            reasons.append("CONCRETE_STRENGTH_CLASS_REQUIRED")
        kind = str(candidate.get("product_kind") or candidate.get("description") or "").casefold()
        if ("ready-mix" in kind or "ready mix" in kind or "betonmortel" in kind) and not candidate.get("importable_as_finished_product", False):
            reasons.append("READY_MIX_NOT_IMPORTABLE_AS_FINISHED_PRODUCT")
    elif family == "masonry_unit":
        if not (tech.get("declared_compressive_strength_mpa") or tech.get("compressive_strength_mpa") or eng.startswith("MASONRY_")):
            reasons.append("MASONRY_COMPRESSIVE_STRENGTH_REQUIRED")
    elif family == "structural_steel_section":
        if not (tech.get("declared_steel_grade") or tech.get("yield_strength_mpa") or eng.startswith("STRUCTURAL_STEEL_")):
            reasons.append("STRUCTURAL_STEEL_GRADE_REQUIRED")
    return not reasons, reasons


def _date_age_days(value: Any) -> int | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(str(value)[:10])
        return max(0, (date.today() - d).days)
    except Exception:
        return None


def _extract_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("products", "candidates", "offers", "items", "capability_records"):
        rows = catalog.get(key)
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    if isinstance(catalog.get("product"), dict):
        return [catalog["product"]]
    return []


def _source_catalogs(workspace: Path) -> list[Path]:
    roots = [
        workspace / "sources" / "global_material_supply",
        workspace / "sources" / "import_candidates",
        workspace / "sources" / "material_supply",
    ]
    result: list[Path] = []
    for root in roots:
        if root.is_dir():
            result.extend(sorted(root.rglob("*.json")))
    return sorted(set(result))


def _fx_records(workspace: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for root in (workspace / "sources" / "fx", workspace / "sources" / "market_prices"):
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            try:
                data = _read(path)
            except Exception:
                continue
            rows = data.get("rates") if isinstance(data.get("rates"), list) else [data]
            for row in rows:
                if isinstance(row, dict):
                    x = dict(row); x["_source"] = str(path); records.append(x)
    return records


def _fx_rate(workspace: Path, source_currency: str, target_currency: str, candidate: dict[str, Any], max_age_days: int) -> tuple[float | None, dict[str, Any] | None]:
    if source_currency == target_currency:
        return 1.0, {"source": "IDENTITY", "rate": 1.0, "as_of_date": date.today().isoformat()}
    embedded = candidate.get("fx_rate_to_project_currency")
    if embedded is not None:
        try:
            rate = float(embedded)
            d = candidate.get("fx_rate_date") or candidate.get("price_date")
            age = _date_age_days(d)
            if rate > 0 and age is not None and age <= max_age_days:
                return rate, {"source": "CANDIDATE_EMBEDDED", "rate": rate, "as_of_date": d}
        except Exception:
            pass
    for rec in _fx_records(workspace):
        base = str(rec.get("base_currency") or rec.get("base") or "").upper()
        quote = str(rec.get("quote_currency") or rec.get("quote") or "").upper()
        try:
            rate = float(rec.get("rate"))
        except Exception:
            continue
        age = _date_age_days(rec.get("as_of_date") or rec.get("date"))
        if age is None or age > max_age_days or rate <= 0:
            continue
        if base == source_currency and quote == target_currency:
            return rate, {"source": rec.get("_source"), "rate": rate, "as_of_date": rec.get("as_of_date") or rec.get("date")}
        if base == target_currency and quote == source_currency:
            return 1.0 / rate, {"source": rec.get("_source"), "rate": 1.0 / rate, "as_of_date": rec.get("as_of_date") or rec.get("date"), "inverted": True}
    return None, None


def _containers(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    result=[candidate]
    for key in ("landed_cost","logistics","cost_components"):
        if isinstance(candidate.get(key),dict): result.append(candidate[key])
    return result


def _amount(candidate: dict[str, Any], name: str) -> float | None:
    aliases = {
        "packing": ("packing", "export_packing", "packaging"),
        "origin_inland": ("origin_inland", "origin_transport", "origin_haulage"),
        "export_handling": ("export_handling", "export_fees"),
        "freight": ("freight", "ocean_freight", "air_freight", "international_freight"),
        "insurance": ("insurance", "cargo_insurance"),
        "destination_handling": ("destination_handling", "port_handling", "terminal_handling"),
        "brokerage": ("brokerage", "customs_brokerage", "clearance"),
        "last_mile": ("last_mile", "last_mile_paramaribo", "destination_transport"),
        "duty_amount": ("duty_amount", "customs_duty_amount", "import_duty_amount"),
        "tax_amount": ("tax_amount", "import_tax_amount", "vat_amount"),
    }
    for c in _containers(candidate):
        for key in aliases.get(name, (name,)):
            if c.get(key) is not None:
                try: return float(c[key])
                except Exception: pass
    return None


def _rate(candidate: dict[str, Any], *names: str) -> float | None:
    for c in _containers(candidate):
        for name in names:
            if c.get(name) is not None:
                try: return float(c[name])
                except Exception: pass
    return None


def _explicit_total(candidate: dict[str, Any]) -> tuple[float | None, str | None]:
    for c in _containers(candidate)[:2]:
        for key in ("landed_cost_total_srd", "delivered_total_srd"):
            if c.get(key) is not None:
                try: return float(c[key]), "SRD"
                except Exception: pass
        for key in ("landed_cost_total", "delivered_total"):
            if c.get(key) is not None:
                try: return float(c[key]), str(c.get("currency") or candidate.get("currency") or "").upper() or None
                except Exception: pass
    return None, None


def _landed_cost(candidate: dict[str, Any], workspace: Path, project_currency: str, destination_city: str | None, policy: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "BLOCKED", "missing": [], "components": {}}
    lc = candidate.get("landed_cost") if isinstance(candidate.get("landed_cost"),dict) else {}
    delivered_to = str(candidate.get("delivered_to") or lc.get("delivered_to") or "")
    if destination_city and delivered_to and destination_city.casefold() not in delivered_to.casefold():
        result["missing"].append("DELIVERY_DESTINATION_PARAMARIBO_REQUIRED")
    explicit, explicit_currency = _explicit_total(candidate)
    qty = candidate.get("quote_quantity") or candidate.get("quantity") or candidate.get("minimum_order_quantity")
    try: qty = float(qty)
    except Exception: qty = None
    if qty is not None and qty <= 0: qty = None
    unit = candidate.get("unit")

    if explicit is not None:
        curr = explicit_currency or str(candidate.get("currency") or "").upper()
        if curr == project_currency:
            total_target = explicit; fx_meta = {"source": "EXPLICIT_PROJECT_CURRENCY_LANDED_TOTAL", "rate": 1.0}
        else:
            rate, fx_meta = _fx_rate(workspace, curr, project_currency, candidate, int(policy.get("fx_max_age_days", 7)))
            if rate is None:
                result["missing"].append("CURRENT_FX_EVIDENCE_REQUIRED"); return result
            total_target = explicit * rate
        result.update({
            "status": "PASSED", "landed_cost_total_srd": round(total_target, 4),
            "landed_cost_per_unit_srd": round(total_target / qty, 6) if qty else None,
            "quote_quantity": qty, "unit": unit, "fx": fx_meta, "basis": "EXPLICIT_DELIVERED_TOTAL",
        })
        return result

    currency = str(candidate.get("currency") or "").upper()
    try: unit_price = float(candidate.get("unit_price"))
    except Exception: unit_price = None
    if not currency: result["missing"].append("SOURCE_CURRENCY_REQUIRED")
    if unit_price is None: result["missing"].append("PRODUCT_UNIT_PRICE_REQUIRED")
    if qty is None: result["missing"].append("QUOTE_QUANTITY_OR_MOQ_REQUIRED")
    if result["missing"]: return result

    product_total = unit_price * qty
    components = {"product_total": product_total}
    mandatory = list(policy.get("mandatory_import_components") or [
        "packing", "origin_inland", "export_handling", "freight", "insurance",
        "destination_handling", "brokerage", "last_mile",
    ])
    for name in mandatory:
        value = _amount(candidate, name)
        if value is None: result["missing"].append(f"{name.upper()}_COST_EVIDENCE_REQUIRED")
        else: components[name] = value

    cif = product_total + sum(components.get(x, 0.0) for x in ("packing", "origin_inland", "export_handling", "freight", "insurance"))
    duty = _amount(candidate, "duty_amount")
    if duty is None:
        duty_rate = _rate(candidate, "duty_rate", "customs_duty_rate", "import_duty_rate")
        duty_basis = str(candidate.get("duty_basis") or lc.get("duty_basis") or "").upper()
        if duty_rate is not None and duty_basis == "CIF": duty = cif * duty_rate
        else: result["missing"].append("CUSTOMS_DUTY_EVIDENCE_REQUIRED")
    if duty is not None: components["duty"] = duty

    tax = _amount(candidate, "tax_amount")
    if tax is None:
        tax_rate = _rate(candidate, "tax_rate", "vat_rate", "import_tax_rate")
        tax_basis = str(candidate.get("tax_basis") or lc.get("tax_basis") or "").upper()
        if tax_rate is not None and tax_basis == "CIF_PLUS_DUTY" and duty is not None: tax = (cif + duty) * tax_rate
        else: result["missing"].append("IMPORT_TAX_EVIDENCE_REQUIRED")
    if tax is not None: components["tax"] = tax

    if result["missing"]: return result
    total_source = sum(components.values())
    rate, fx_meta = _fx_rate(workspace, currency, project_currency, candidate, int(policy.get("fx_max_age_days", 7)))
    if rate is None:
        result["missing"].append("CURRENT_FX_EVIDENCE_REQUIRED"); return result
    total_target = total_source * rate
    result.update({
        "status": "PASSED", "components": components,
        "landed_cost_total_source_currency": round(total_source, 6), "source_currency": currency,
        "landed_cost_total_srd": round(total_target, 4), "landed_cost_per_unit_srd": round(total_target / qty, 6),
        "quote_quantity": qty, "unit": unit, "fx": fx_meta,
        "basis": "CALCULATED_FROM_EXPLICIT_COMPONENT_EVIDENCE",
    })
    return result


def _candidate_from_row(row: dict[str, Any], catalog: dict[str, Any], source: Path, repository: Path) -> dict[str, Any]:
    md = catalog.get("metadata") if isinstance(catalog.get("metadata"), dict) else catalog
    item = json.loads(json.dumps(row))
    for key in ("supplier_id", "supplier_name", "country_code", "region_name", "city", "currency", "source_name", "source_url", "availability_verified_date", "price_date", "confidence"):
        if item.get(key) is None and md.get(key) is not None:
            item[key] = md[key]
    item["source_reference"] = _repo_ref(source, repository)
    return item


def _acquire_configured_https_sources(repository: Path, workspace: Path, manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    urls = manifest.get("global_material_source_urls") if isinstance(manifest, dict) else None
    urls = urls if isinstance(urls, list) else []
    outdir = workspace / "sources" / "global_material_supply" / "acquired"
    acquired, failed = [], []
    if not policy.get("allow_configured_https_json_sources", True):
        return {"acquired": acquired, "failed": failed}
    for idx, url in enumerate(urls):
        if not isinstance(url, str) or not url.lower().startswith("https://"):
            failed.append({"url": url, "reason": "HTTPS_JSON_SOURCE_REQUIRED"}); continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Project-Phoenix/1.0"})
            with urllib.request.urlopen(req, timeout=float(policy.get("https_timeout_seconds", 12))) as response:
                body = response.read(int(policy.get("https_max_bytes", 5_000_000)) + 1)
            if len(body) > int(policy.get("https_max_bytes", 5_000_000)): raise ValueError("SOURCE_TOO_LARGE")
            value = json.loads(body.decode("utf-8"))
            if not isinstance(value, dict): raise ValueError("JSON_OBJECT_REQUIRED")
            path = outdir / f"{idx:03d}_configured_global_material_source.json"
            _write(path, value); acquired.append(_repo_ref(path, repository))
        except Exception as exc:
            failed.append({"url": url, "reason": type(exc).__name__, "detail": str(exc)[:300]})
    return {"acquired": acquired, "failed": failed}


def build_global_material_sourcing_context(
    *, repository: Path, workspace: Path, project_id: str,
    project_context: dict[str, Any], local_selection_register: dict[str, Any],
    manifest: dict[str, Any], policy: dict[str, Any] | None = None,
) -> GlobalMaterialSourcingResult:
    repository = Path(repository).resolve(); workspace = Path(workspace).resolve()
    if policy is None:
        policy_path = repository / "configs" / "phoenix" / "global_material_sourcing_policy_v1_0.json"
        try:
            policy = _read(policy_path) if policy_path.is_file() else {}
        except Exception:
            policy = {}
    policy = dict(policy or {})
    project_currency = _project_currency(project_context, manifest) or "SRD"
    dest = _destination(project_context)
    remote = _acquire_configured_https_sources(repository, workspace, manifest, policy)

    source_paths = _source_catalogs(workspace)
    candidates: list[dict[str, Any]] = []
    for source in source_paths:
        try: catalog = _read(source)
        except Exception: continue
        for row in _extract_rows(catalog): candidates.append(_candidate_from_row(row, catalog, source, repository))

    comparisons: list[dict[str, Any]] = []; selections: list[dict[str, Any]] = []; blockers: list[dict[str, Any]] = []; warnings: list[str] = []
    requirements = list(local_selection_register.get("selections") or [])
    for req in requirements:
        if not isinstance(req, dict): continue
        req_id = str(req.get("requirement_id") or "UNKNOWN_REQUIREMENT"); family = str(req.get("material_family") or "")
        selected = req.get("selected_product") if isinstance(req.get("selected_product"), dict) else None
        existing_qualified = bool(req.get("commercial_availability_confirmed")) and str(req.get("engineering_qualification_status") or "").upper() in {"QUALIFIED", "ENGINEERING_QUALIFIED"} and selected is not None and bool(selected.get("engineering_material_id"))
        if existing_qualified:
            keep = json.loads(json.dumps(req)); keep["supply_origin"] = "LOCAL"; keep["procurement_route"] = "LOCAL_SELECTED"; selections.append(keep)
            comparisons.append({"requirement_id": req_id, "status": "LOCAL_QUALIFIED_SELECTED", "selected_product_id": selected.get("product_id")}); continue

        rows = [c for c in candidates if str(c.get("material_family") or "") == family]
        evaluated: list[dict[str, Any]] = []
        for c in rows:
            status = str(c.get("availability_status") or c.get("source_availability_status") or "").upper()
            cert_ok, cert_reasons = _certified(c); eng_ok, eng_reasons = _engineering_qualified(c, family); freshness_ok, freshness_reasons = _freshness(c, policy); availability_ok = status in AVAILABLE
            landed = _landed_cost(c, workspace, project_currency, dest.get("city") or "Paramaribo", policy)
            origin = str(c.get("country_code") or c.get("origin_country_code") or "").upper(); local = origin == str(dest.get("country_code") or "").upper() and bool(origin)
            valid = availability_ok and cert_ok and eng_ok and freshness_ok and landed.get("status") == "PASSED"
            evaluated.append({"product_id": c.get("product_id"), "supplier_name": c.get("supplier_name"), "material_family": family, "origin_country_code": origin or None, "supply_origin": "LOCAL" if local else "IMPORT", "availability_ok": availability_ok, "certification_ok": cert_ok, "engineering_qualification_ok": eng_ok, "freshness_ok": freshness_ok, "freshness_reasons": freshness_reasons, "technical_reasons": eng_reasons, "certification_reasons": cert_reasons, "landed_cost": landed, "lead_time_days": c.get("lead_time_days"), "source_reference": c.get("source_reference"), "valid_for_selection": valid, "candidate": c})
        valid = [x for x in evaluated if x["valid_for_selection"]]
        valid.sort(key=lambda x: (math.inf if x["landed_cost"].get("landed_cost_per_unit_srd") is None else float(x["landed_cost"]["landed_cost_per_unit_srd"]), math.inf if x.get("lead_time_days") is None else float(x["lead_time_days"])))
        if valid:
            winner = valid[0]; product = json.loads(json.dumps(winner["candidate"])); product["landed_cost"] = winner["landed_cost"]; product["procurement_route"] = winner["supply_origin"]; product["delivery_destination"] = dest.get("location") or dest.get("city") or "Paramaribo"; product["engineering_qualification_status"] = "ENGINEERING_QUALIFIED"
            selection = json.loads(json.dumps(req)); selection.update({"selection_status": "SUPPLY_CONFIRMED", "commercial_availability_confirmed": True, "engineering_qualification_status": "ENGINEERING_QUALIFIED", "selected_product": product, "supply_origin": winner["supply_origin"], "procurement_route": "LOCAL" if winner["supply_origin"] == "LOCAL" else "INTERNATIONAL_IMPORT", "automatic_ordering": False}); selections.append(selection)
            comparisons.append({"requirement_id": req_id, "status": "CHEAPEST_TECHNICALLY_VALID_LANDED_OPTION_SELECTED", "candidate_count": len(evaluated), "valid_candidate_count": len(valid), "selected_product_id": product.get("product_id"), "selected_supplier": product.get("supplier_name"), "selected_supply_origin": winner["supply_origin"], "selected_landed_cost_per_unit_srd": winner["landed_cost"].get("landed_cost_per_unit_srd"), "evaluated_candidates": [{k:v for k,v in x.items() if k != "candidate"} for x in evaluated]})
        else:
            reasons = []
            if not evaluated: reasons.append("GLOBAL_SUPPLIER_EVIDENCE_REQUIRED")
            elif not any(x["certification_ok"] and x["engineering_qualification_ok"] for x in evaluated): reasons.append("CERTIFIED_ENGINEERING_QUALIFIED_PRODUCT_REQUIRED")
            elif not any(x["landed_cost"].get("status") == "PASSED" for x in evaluated): reasons.append("COMPLETE_LANDED_COST_TO_PARAMARIBO_EVIDENCE_REQUIRED")
            else: reasons.append("AVAILABLE_VALID_PRODUCT_REQUIRED")
            selection = json.loads(json.dumps(req)); selection["supply_origin"] = None; selection["procurement_route"] = "BLOCKED"; selections.append(selection)
            blockers.append({"requirement_id": req_id, "material_family": family, "reasons": reasons}); comparisons.append({"requirement_id": req_id, "status": "BLOCKED", "candidate_count": len(evaluated), "reasons": reasons, "evaluated_candidates": [{k:v for k,v in x.items() if k != "candidate"} for x in evaluated]})

    structural_items = [x for x in selections if _is_structural_requirement(x)]
    all_supply = bool(selections) and all(bool(x.get("selected_product")) and bool(x.get("commercial_availability_confirmed")) for x in selections)
    all_structural_qualified = bool(structural_items) and all(str(x.get("engineering_qualification_status") or "").upper() in {"QUALIFIED", "ENGINEERING_QUALIFIED"} and isinstance(x.get("selected_product"), dict) and bool(x["selected_product"].get("engineering_material_id")) for x in structural_items)
    imported = [x for x in selections if x.get("procurement_route") == "INTERNATIONAL_IMPORT"]
    import_landed_complete = all(isinstance(x.get("selected_product"), dict) and isinstance(x["selected_product"].get("landed_cost"), dict) and x["selected_product"]["landed_cost"].get("status") == "PASSED" for x in imported)

    structural_register = {"schema_version": "phoenix.structural-material-selection-register/1.0", "engine_version": VERSION, "project_id": project_id, "as_of_date": date.today().isoformat(), "destination": dest, "project_currency": project_currency, "status": "PASSED" if all_supply and all_structural_qualified and import_landed_complete else "BLOCKED", "all_requirements_supply_confirmed": all_supply, "all_requirements_commercially_available": all_supply, "all_structural_requirements_engineering_qualified": all_structural_qualified, "all_imported_selections_landed_cost_complete": import_landed_complete, "local_first_policy": True, "international_fallback_enabled": True, "cheapest_selection_basis": "LOWEST_COMPLETE_LANDED_COST_TO_PROJECT_DESTINATION_AMONG_TECHNICALLY_VALID_CERTIFIED_OPTIONS", "selections": selections, "automatic_ordering": False, "automatic_product_substitution": False, "professional_review_required": True, "production_release": "LOCKED"}
    sourcing_register = {"schema_version": "phoenix.global-material-sourcing-register/1.0", "engine_version": VERSION, "project_id": project_id, "status": structural_register["status"], "destination": dest, "project_currency": project_currency, "source_catalog_count": len(source_paths), "candidate_count": len(candidates), "configured_https_acquisition": remote, "implicit_web_search_used": False, "configured_https_json_sources_enabled": True, "selected_import_count": len(imported), "blocker_count": len(blockers), "blockers": blockers, "automatic_ordering": False, "professional_review_required": True, "production_release": "LOCKED"}
    landed_register = {"schema_version": "phoenix.landed-cost-register/1.0", "project_id": project_id, "currency": project_currency, "destination": dest, "selected_imports": [{"requirement_id": x.get("requirement_id"), "product_id": (x.get("selected_product") or {}).get("product_id"), "supplier_name": (x.get("selected_product") or {}).get("supplier_name"), "landed_cost": (x.get("selected_product") or {}).get("landed_cost"), "source_reference": (x.get("selected_product") or {}).get("source_reference")} for x in imported], "status": "PASSED" if import_landed_complete else "BLOCKED", "tax_or_duty_fabrication": False, "freight_fabrication": False, "fx_fabrication": False}
    candidate_comparison = {"schema_version": "phoenix.global-material-candidate-comparison/1.0", "project_id": project_id, "selection_rule": "CHEAPEST_COMPLETE_LANDED_COST_AFTER_CERTIFICATION_AND_ENGINEERING_QUALIFICATION", "requirements": comparisons}
    if remote["failed"]: warnings.append("Een of meer geconfigureerde HTTPS-bronnen konden niet worden opgehaald; geen stilzwijgende vervanging toegepast.")
    return GlobalMaterialSourcingResult(structural_register["status"], sourcing_register, candidate_comparison, landed_register, structural_register, blockers, warnings)
