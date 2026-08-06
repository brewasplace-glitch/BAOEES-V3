from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping

MODE_CERTIFIED = "CERTIFIED_REQUIRED"
MODE_UNCERTIFIED = "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"
MARKER_RE = re.compile(r"\[PHOENIX_MATERIAL_CERTIFICATION_MODE=([A-Z_]+)\]")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _walk(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def resolve_mode(context: Any) -> str:
    """Resolve dashboard mode from structured fields or the durable brief marker.

    The default deliberately remains strict/certified to preserve current Phoenix behaviour.
    """
    for item in _walk(context):
        if isinstance(item, Mapping):
            raw = item.get("material_certification_mode")
            if raw in {MODE_CERTIFIED, MODE_UNCERTIFIED}:
                return str(raw)
            if "certified_materials_required" in item:
                return MODE_CERTIFIED if bool(item.get("certified_materials_required")) else MODE_UNCERTIFIED
        elif isinstance(item, str):
            match = MARKER_RE.search(item)
            if match and match.group(1) in {MODE_CERTIFIED, MODE_UNCERTIFIED}:
                return match.group(1)
    return MODE_CERTIFIED


def _candidate_workspace_from_string(value: str) -> Path | None:
    norm = value.replace("\\", "/")
    token = "projects/runtime/"
    idx = norm.lower().find(token)
    if idx < 0:
        return None
    tail = norm[idx + len(token):].strip("/")
    if not tail:
        return None
    project_id = tail.split("/", 1)[0]
    if not project_id:
        return None
    return PROJECT_ROOT / "projects" / "runtime" / project_id


def resolve_workspace(context: Any) -> Path | None:
    project_ids: list[str] = []
    for item in _walk(context):
        if isinstance(item, Mapping):
            for key in ("workspace", "project_workspace"):
                value = item.get(key)
                if isinstance(value, str):
                    candidate = Path(value)
                    if not candidate.is_absolute():
                        candidate = PROJECT_ROOT / candidate
                    if "projects" in candidate.parts and "runtime" in candidate.parts:
                        return candidate
            value = item.get("project_id")
            if isinstance(value, str) and value.strip():
                project_ids.append(value.strip())
        elif isinstance(item, Path):
            candidate = _candidate_workspace_from_string(str(item))
            if candidate:
                return candidate
        elif isinstance(item, str):
            candidate = _candidate_workspace_from_string(item)
            if candidate:
                return candidate
    for project_id in project_ids:
        candidate = PROJECT_ROOT / "projects" / "runtime" / project_id
        if candidate.exists():
            return candidate
    return (PROJECT_ROOT / "projects" / "runtime" / project_ids[0]) if project_ids else None


def _mode_from_workspace(workspace: Path | None) -> str:
    if not workspace:
        return MODE_CERTIFIED
    candidates = [
        workspace / "results" / "session_adapters" / "architecture" / "architectural_session_intake.json",
        workspace / "project_manifest.json",
        workspace / "digital_twin" / "project_state.json",
    ]
    for path in candidates:
        if path.is_file():
            mode = resolve_mode(_read_json(path))
            if mode == MODE_UNCERTIFIED:
                return mode
    # Session files are durable outside the workspace. Match project id and read newest first.
    session_dir = PROJECT_ROOT / "outputs" / "runtime" / "phoenix_start_v3_sessions"
    if session_dir.is_dir():
        project_id = workspace.name
        for path in sorted(session_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = _read_json(path)
            if isinstance(data, Mapping) and data.get("bootstrap", {}).get("project_id") == project_id:
                mode = resolve_mode(data)
                if mode == MODE_UNCERTIFIED:
                    return mode
                if mode == MODE_CERTIFIED:
                    return mode
    return MODE_CERTIFIED


def mode_from_context(context: Any) -> str:
    direct = resolve_mode(context)
    if direct == MODE_UNCERTIFIED:
        return direct
    return _mode_from_workspace(resolve_workspace(context))


def _selection_register(workspace: Path) -> Path | None:
    base = workspace / "results" / "session_adapters" / "architecture"
    for name in ("structural_material_selection_register.json", "local_material_selection_register.json"):
        path = base / name
        if path.is_file():
            return path
    return None


def _qualified(selection: Mapping[str, Any]) -> bool:
    status = str(selection.get("engineering_qualification_status") or "").upper()
    if "NOT_QUALIFIED" in status or "REQUIRED" in status or not status:
        return False
    if "QUALIFIED" in status or status in {"PASSED", "APPROVED"}:
        return True
    product = selection.get("selected_product")
    if isinstance(product, Mapping):
        certs = product.get("certifications")
        complete = product.get("structural_technical_properties_complete")
        return bool(certs) and bool(complete)
    return False


def _commercially_available(selection: Mapping[str, Any]) -> bool:
    if selection.get("commercial_availability_confirmed") is True:
        return True
    status = str(selection.get("selection_status") or "").upper()
    return status in {"LOCAL_AVAILABILITY_CONFIRMED", "AVAILABLE", "AVAILABLE_TO_ORDER"}


def _candidate_available(candidate: Mapping[str, Any]) -> bool:
    if candidate.get("commercial_availability_confirmed") is True:
        return True
    for key in ("selection_status", "availability_status", "source_availability_status"):
        status = str(candidate.get(key) or "").upper()
        if status in {"LOCAL_AVAILABILITY_CONFIRMED", "ALTERNATIVE_AVAILABILITY_CONFIRMED", "AVAILABLE", "AVAILABLE_TO_ORDER", "IN_STOCK", "COMMERCIAL_AVAILABILITY_CONFIRMED"}:
            return True
    return False


def _candidate_qualified(candidate: Mapping[str, Any]) -> bool:
    status = str(candidate.get("engineering_qualification_status") or "").upper()
    if status and "NOT_QUALIFIED" not in status and "REQUIRED" not in status and ("QUALIFIED" in status or status in {"PASSED", "APPROVED"}):
        return True
    certs = candidate.get("certifications")
    complete = candidate.get("structural_technical_properties_complete")
    return bool(certs) and bool(complete)


def _normalize_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value.get("selected_product"), Mapping):
        product = dict(value["selected_product"])
        for key in (
            "material_family", "commercial_availability_confirmed", "selection_status",
            "availability_status", "source_availability_status", "engineering_qualification_status",
            "selection_score", "supply_origin", "country_code", "region_name", "city",
        ):
            if key not in product and key in value:
                product[key] = value.get(key)
        return product
    return dict(value)


def _candidate_identity(candidate: Mapping[str, Any]) -> str:
    for key in ("product_id", "supplier_product_code", "source_url", "source_reference", "description"):
        value = candidate.get(key)
        if value:
            return f"{key}:{value}"
    return json.dumps(candidate, sort_keys=True, ensure_ascii=False, default=str)[:500]


def _candidate_pool(workspace: Path, selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    family = str(selection.get("material_family") or "")
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        candidate = _normalize_candidate(value)
        candidate_family = str(candidate.get("material_family") or family)
        if family and candidate_family and candidate_family != family:
            return
        candidate["material_family"] = candidate_family or family
        if not _candidate_available(candidate):
            return
        ident = _candidate_identity(candidate)
        if ident in seen:
            return
        seen.add(ident)
        found.append(candidate)

    for key in ("alternatives", "candidates"):
        values = selection.get(key)
        if isinstance(values, list):
            for value in values:
                add(value)

    base = workspace / "results" / "session_adapters" / "architecture"
    for name in (
        "global_material_candidate_comparison.json",
        "global_material_candidate_evaluation_register.json",
        "global_material_sourcing_register.json",
        "local_material_selection_register.json",
        "structural_material_selection_register.json",
    ):
        path = base / name
        data = _read_json(path) if path.is_file() else None
        if data is None:
            continue
        for item in _walk(data):
            if not isinstance(item, Mapping):
                continue
            blob_family = str(item.get("material_family") or "")
            if blob_family == family or (isinstance(item.get("selected_product"), Mapping) and str(item["selected_product"].get("material_family") or "") == family):
                add(item)
    return found


def _alternative_sort_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    country = str(candidate.get("country_code") or "").upper()
    origin_rank = {"SR": 0, "NL": 1, "BE": 2}.get(country, 3)
    price = candidate.get("unit_price")
    try:
        price_key = float(price) if price is not None else float("inf")
    except Exception:
        price_key = float("inf")
    score = candidate.get("selection_score")
    try:
        score_key = -float(score) if score is not None else 0.0
    except Exception:
        score_key = 0.0
    return (origin_rank, price_key, score_key, _candidate_identity(candidate))


def _choose_available_alternative(workspace: Path, selection: Mapping[str, Any], mode: str) -> tuple[dict[str, Any] | None, int]:
    current_id = _candidate_identity(_normalize_candidate(selection.get("selected_product") or {})) if isinstance(selection.get("selected_product"), Mapping) else None
    candidates = []
    for candidate in _candidate_pool(workspace, selection):
        if current_id and _candidate_identity(candidate) == current_id:
            continue
        if mode == MODE_CERTIFIED and not _candidate_qualified(candidate):
            continue
        candidates.append(candidate)
    candidates.sort(key=_alternative_sort_key)
    return (candidates[0] if candidates else None, len(candidates))


def resolve_material_availability(workspace: Path, mode: str | None = None) -> dict[str, Any]:
    """Keep design engineering moving when supply is unknown/unavailable.

    Availability never asserts a product exists. Phoenix first searches already acquired local/global candidate
    evidence for a same-family available alternative. When none is evidenced, the design keeps the required
    material class as a procurement-unresolved design placeholder. Construction/procurement release remains locked.
    """
    mode = mode or _mode_from_workspace(workspace)
    path = _selection_register(workspace)
    data = _read_json(path) if path else None
    selections = data.get("selections", []) if isinstance(data, MutableMapping) else []
    resolved: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    alternatives: list[dict[str, Any]] = []
    unresolved_design_class: list[str] = []

    for raw in selections:
        if not isinstance(raw, MutableMapping):
            continue
        req_id = str(raw.get("requirement_id") or "")
        family = str(raw.get("material_family") or "")
        design_class = resolve_required_design_class(workspace, raw)
        if _commercially_available(raw) and isinstance(raw.get("selected_product"), Mapping):
            raw["availability_resolution_status"] = "SELECTED_PRODUCT_AVAILABLE"
            raw["availability_blocks_engineering"] = False
            continue

        alt, alt_count = _choose_available_alternative(workspace, raw, mode)
        if alt is not None:
            previous = raw.get("selected_product") if isinstance(raw.get("selected_product"), Mapping) else None
            raw["previous_selected_product"] = previous
            raw["selected_product"] = alt
            raw["selection_status"] = "ALTERNATIVE_AVAILABILITY_CONFIRMED"
            raw["commercial_availability_confirmed"] = True
            raw["availability_resolution_status"] = "AVAILABLE_ALTERNATIVE_SELECTED"
            raw["availability_blocks_engineering"] = False
            raw["availability_blocks_procurement_release"] = False
            raw["procurement_route"] = "AVAILABLE_ALTERNATIVE_SELECTED"
            raw["alternative_substitution_requires_recalculation"] = True
            raw["assumed_design_material_class"] = design_class
            alternatives.append({
                "requirement_id": req_id,
                "material_family": family,
                "required_design_class": design_class,
                "selected_alternative_product_id": alt.get("product_id"),
                "selected_alternative_supplier": alt.get("supplier_name"),
                "availability_status": alt.get("availability_status") or alt.get("source_availability_status") or "AVAILABLE",
                "certification_status": "QUALIFIED" if _candidate_qualified(alt) else "UNCERTIFIED",
                "unit_price": alt.get("unit_price"),
                "currency": alt.get("currency"),
                "unit": alt.get("unit"),
                "source_reference": alt.get("source_reference") or alt.get("source_url"),
                "selection_basis": "SAME_MATERIAL_FAMILY_AVAILABLE_ALTERNATIVE; LOCAL_FIRST_THEN_KNOWN_PRICE",
                "candidate_count_considered": alt_count,
                "recalculation_required": True,
            })
            resolved.append({"requirement_id": req_id, "status": "AVAILABLE_ALTERNATIVE_SELECTED"})
            continue

        if not design_class:
            unresolved_design_class.append(req_id or family or "UNKNOWN")
        product = raw.get("selected_product") if isinstance(raw.get("selected_product"), Mapping) else {}
        raw["availability_resolution_status"] = "NO_AVAILABLE_ALTERNATIVE_FOUND_DESIGN_CONTINUES"
        raw["availability_blocks_engineering"] = False
        raw["availability_blocks_procurement_release"] = True
        raw["commercial_availability_confirmed"] = False
        raw["procurement_route"] = "UNRESOLVED_AVAILABILITY_DESIGN_PLACEHOLDER"
        raw["assumed_design_material_class"] = design_class
        raw["design_assumption_basis"] = "REQUIRED_CLASS_DESIGN_PLACEHOLDER_AVAILABILITY_UNRESOLVED"
        raw["calculation_eligibility_status"] = "ELIGIBLE_BY_REQUIRED_DESIGN_CLASS_PLACEHOLDER" if design_class else "DESIGN_CLASS_REQUIRED"
        raw["unavailable_at_run_time"] = True
        unavailable.append({
            "requirement_id": req_id,
            "material_family": family,
            "element_role": raw.get("element_role"),
            "design_product_id": product.get("product_id"),
            "design_description": product.get("description"),
            "required_design_class": design_class,
            "availability_status": raw.get("selection_status") or product.get("availability_status") or "AVAILABILITY_UNKNOWN",
            "availability_qualification": "UNAVAILABLE_OR_NOT_CONFIRMED_AT_RUN_TIME",
            "alternative_search_status": "NO_EVIDENCED_AVAILABLE_ALTERNATIVE_FOUND",
            "candidate_count_considered": alt_count,
            "engineering_status": "DESIGN_CONTINUES_WITH_REQUIRED_CLASS_PLACEHOLDER" if design_class else "DESIGN_CLASS_REQUIRED",
            "cost_status": "PRICE_UNRESOLVED_UNLESS_SEPARATE_VALID_PRICE_EVIDENCE_EXISTS",
            "unit_price_if_present_not_confirmed_by_availability": product.get("unit_price"),
            "currency": product.get("currency"),
            "unit": product.get("unit"),
            "procurement_release": "LOCKED_PENDING_AVAILABILITY_RESOLUTION",
        })
        resolved.append({"requirement_id": req_id, "status": "DESIGN_CONTINUES_PROCUREMENT_UNRESOLVED"})

    out_dir = workspace / "results" / "session_adapters" / "architecture"
    availability_path = out_dir / "material_availability_resolution_register.json"
    unavailable_json = out_dir / "unavailable_materials_register.json"
    unavailable_csv = out_dir / "unavailable_materials_register.csv"
    alternatives_json = out_dir / "available_alternative_materials_register.json"
    alternatives_csv = out_dir / "available_alternative_materials_register.csv"

    register = {
        "schema_version": "phoenix.material-availability-resolution-register/1.1",
        "project_id": workspace.name,
        "generated_utc": _now(),
        "material_certification_mode": mode,
        "availability_blocks_engineering": False,
        "alternative_search_policy": "SAME_FAMILY; EXISTING_LOCAL_GLOBAL_EVIDENCE; CERTIFIED_ONLY_WHEN_CERTIFIED_MODE",
        "no_alternative_policy": "CONTINUE_ENGINEERING_WITH_REQUIRED_CLASS_DESIGN_PLACEHOLDER",
        "available_alternative_count": len(alternatives),
        "unavailable_material_count": len(unavailable),
        "unresolved_design_class_requirements": unresolved_design_class,
        "resolutions": resolved,
        "available_alternatives": alternatives,
        "unavailable_materials": unavailable,
        "production_release": "LOCKED_IF_UNAVAILABLE_OR_UNCERTIFIED_MATERIALS_PRESENT",
    }
    _write_json(availability_path, register)
    _write_json(unavailable_json, {
        "schema_version": "phoenix.unavailable-materials-register/1.1",
        "project_id": workspace.name,
        "generated_utc": _now(),
        "count": len(unavailable),
        "materials": unavailable,
        "engineering_policy": "DESIGN_CONTINUES; PROCUREMENT_AVAILABILITY_REMAINS_UNRESOLVED",
        "production_release": "LOCKED_PENDING_AVAILABILITY_RESOLUTION" if unavailable else "NO_AVAILABILITY_LOCK_FROM_THIS_REGISTER",
    })
    _write_json(alternatives_json, {
        "schema_version": "phoenix.available-alternative-materials-register/1.1",
        "project_id": workspace.name,
        "generated_utc": _now(),
        "count": len(alternatives),
        "materials": alternatives,
        "automatic_substitution_basis": "USER_AUTHORIZED_AVAILABILITY_CONTINUATION; SAME_MATERIAL_FAMILY; RECALCULATION_REQUIRED",
    })

    def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        if not fields:
            fields = ["requirement_id", "material_family", "status"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key) for key in fields})
    write_csv(unavailable_csv, unavailable)
    write_csv(alternatives_csv, alternatives)

    if isinstance(data, MutableMapping) and path:
        data["material_availability_engineering_policy"] = "NON_BLOCKING_FOR_DESIGN"
        data["material_availability_resolution_register"] = availability_path.relative_to(PROJECT_ROOT).as_posix()
        data["unavailable_material_count"] = len(unavailable)
        data["available_alternative_material_count"] = len(alternatives)
        _write_json(path, data)
    return register


_FAMILY_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "structural_concrete": (re.compile(r"\bC\d{1,2}/\d{1,2}\b", re.I),),
    "reinforcement_steel": (re.compile(r"\bB\d{3}[ABC]?\b", re.I), re.compile(r"\bFeB\s*\d{3}\b", re.I)),
    "structural_timber": (re.compile(r"\b(?:C|D)\d{2}\b", re.I), re.compile(r"\bGL\s*\d{2}[ch]\b", re.I)),
    "masonry_unit": (re.compile(r"\b(?:MASONRY|METSELWERK)[-_ ]?(?:CLASS|KLASSE)?\s*[A-Z0-9./-]+\b", re.I),),
}


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _extract_class_from_value(family: str, value: Any) -> str | None:
    patterns = _FAMILY_PATTERNS.get(family, ())
    for text in _strings(value):
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return re.sub(r"\s+", "", match.group(0).upper())
    return None


def resolve_required_design_class(workspace: Path, selection: Mapping[str, Any]) -> str | None:
    family = str(selection.get("material_family") or "")
    # Prefer requirement/selection-specific evidence.
    direct = _extract_class_from_value(family, selection)
    if direct:
        return direct
    base = workspace / "results" / "session_adapters" / "architecture"
    for name in (
        "local_material_requirements.json",
        "structural_project_profile.json",
        "architectural_structural_handoff.json",
        "architectural_model.json",
    ):
        path = base / name
        data = _read_json(path) if path.is_file() else None
        if data is None:
            continue
        # First narrow to matching family / requirement id when possible.
        req_id = str(selection.get("requirement_id") or "")
        matching: list[Any] = []
        for item in _walk(data):
            if isinstance(item, Mapping):
                blob = json.dumps(item, ensure_ascii=False, default=str).lower()
                if req_id and req_id.lower() in blob:
                    matching.append(item)
                elif family and family.lower() in blob:
                    matching.append(item)
        for item in matching:
            found = _extract_class_from_value(family, item)
            if found:
                return found
    return None


def _product_field(selection: Mapping[str, Any], key: str) -> Any:
    product = selection.get("selected_product")
    if isinstance(product, Mapping) and key in product:
        return product.get(key)
    return selection.get(key)


def build_uncertified_material_register(workspace: Path) -> dict[str, Any]:
    resolve_material_availability(workspace, MODE_UNCERTIFIED)
    path = _selection_register(workspace)
    data = _read_json(path) if path else None
    selections = data.get("selections", []) if isinstance(data, Mapping) else []
    records: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for raw in selections:
        if not isinstance(raw, MutableMapping):
            continue
        if _qualified(raw):
            continue
        if not _commercially_available(raw) or not isinstance(raw.get("selected_product"), Mapping):
            continue
        design_class = resolve_required_design_class(workspace, raw)
        req_id = str(raw.get("requirement_id") or "")
        if not design_class:
            unresolved.append(req_id or str(raw.get("material_family") or "UNKNOWN"))
        product = raw.get("selected_product") or {}
        raw["certification_status"] = "UNCERTIFIED"
        raw["certified"] = False
        raw["material_certification_mode"] = MODE_UNCERTIFIED
        raw["calculation_eligibility_status"] = (
            "ELIGIBLE_BY_REQUIRED_DESIGN_CLASS_ASSUMPTION" if design_class else "DESIGN_CLASS_REQUIRED"
        )
        raw["assumed_design_material_class"] = design_class
        raw["design_assumption_basis"] = "REQUIRED_CLASS_NOT_PRODUCT_VERIFIED"
        raw["verification_required_before_construction_release"] = True
        raw["cost_inclusion_policy"] = "INCLUDE_CONFIRMED_LOCAL_PRICE"
        if str(raw.get("procurement_route") or "").upper() == "BLOCKED":
            raw["procurement_route"] = "LOCAL_UNCERTIFIED_DESIGN_ASSUMPTION"
        records.append({
            "requirement_id": req_id,
            "material_family": raw.get("material_family"),
            "element_role": raw.get("element_role"),
            "product_id": product.get("product_id"),
            "supplier_name": product.get("supplier_name"),
            "description": product.get("description"),
            "availability_status": raw.get("selection_status") or product.get("availability_status"),
            "certification_status": "UNCERTIFIED",
            "engineering_qualification_original": raw.get("engineering_qualification_status"),
            "required_design_class": design_class,
            "design_assumption_basis": "REQUIRED_CLASS_NOT_PRODUCT_VERIFIED",
            "unit_price": product.get("unit_price"),
            "currency": product.get("currency"),
            "unit": product.get("unit"),
            "price_source": product.get("source_reference") or product.get("source_url"),
            "cost_inclusion_policy": "INCLUDE_CONFIRMED_LOCAL_PRICE",
            "verification_before_construction_release": "REQUIRED",
        })
    if isinstance(data, MutableMapping) and path:
        data["material_certification_mode"] = MODE_UNCERTIFIED
        data["uncertified_material_count"] = len(records)
        data["uncertified_material_register"] = str(
            (workspace / "results" / "session_adapters" / "architecture" / "uncertified_materials_register.json")
            .relative_to(PROJECT_ROOT).as_posix()
        )
        _write_json(path, data)

    out_dir = workspace / "results" / "session_adapters" / "architecture"
    json_path = out_dir / "uncertified_materials_register.json"
    csv_path = out_dir / "uncertified_materials_register.csv"
    mode_path = out_dir / "material_certification_mode_register.json"
    register = {
        "schema_version": "phoenix.uncertified-materials-register/1.0",
        "project_id": workspace.name,
        "generated_utc": _now(),
        "material_certification_mode": MODE_UNCERTIFIED,
        "certification_gate_for_design": "BYPASS_ONLY_FOR_CONFIRMED_LOCAL_AVAILABILITY",
        "product_properties_claimed_as_verified": False,
        "calculation_basis": "REQUIRED_DESIGN_CLASS_AS_EXPLICIT_UNVERIFIED_DESIGN_ASSUMPTION",
        "construction_release": "LOCKED_PENDING_MATERIAL_VERIFICATION",
        "count": len(records),
        "unresolved_design_class_requirements": unresolved,
        "materials": records,
    }
    _write_json(json_path, register)
    _write_json(mode_path, {
        "schema_version": "phoenix.material-certification-mode/1.0",
        "project_id": workspace.name,
        "mode": MODE_UNCERTIFIED,
        "uncertified_material_count": len(records),
        "unresolved_design_class_requirements": unresolved,
        "cost_policy": "LOCAL_CONFIRMED_PRICE_INCLUDED_EVEN_WHEN_UNCERTIFIED",
        "solver_policy": "REQUIRED_CLASS_ASSUMPTION_ALLOWED; PRODUCT_PROPERTIES_NOT_ASSERTED_AS_VERIFIED",
        "production_release": "LOCKED",
        "generated_utc": _now(),
    })
    fields = [
        "requirement_id", "material_family", "element_role", "product_id", "supplier_name", "description",
        "availability_status", "certification_status", "engineering_qualification_original", "required_design_class",
        "design_assumption_basis", "unit_price", "currency", "unit", "price_source", "cost_inclusion_policy",
        "verification_before_construction_release",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row.get(key) for key in fields})
    return register


def _append_outputs(result: Any, paths: Iterable[Path]) -> Any:
    if not isinstance(result, MutableMapping):
        return result
    outputs = result.setdefault("outputs", [])
    if isinstance(outputs, list):
        for path in paths:
            try:
                rel = path.relative_to(PROJECT_ROOT).as_posix()
            except Exception:
                rel = str(path)
            if path.exists() and rel not in outputs:
                outputs.append(rel)
    return result


def postprocess_architecture_result(result: Any, *, args: Any = (), kwargs: Any = None) -> Any:
    context = {"args": args, "kwargs": kwargs or {}, "result": result}
    mode = mode_from_context(context)
    workspace = resolve_workspace(context)
    if not workspace:
        return result
    availability = resolve_material_availability(workspace, mode)
    base = workspace / "results" / "session_adapters" / "architecture"
    _append_outputs(result, [
        base / "material_availability_resolution_register.json",
        base / "unavailable_materials_register.json",
        base / "unavailable_materials_register.csv",
        base / "available_alternative_materials_register.json",
        base / "available_alternative_materials_register.csv",
    ])
    register = None
    if mode == MODE_UNCERTIFIED:
        register = build_uncertified_material_register(workspace)
        _append_outputs(result, [
            base / "uncertified_materials_register.json",
            base / "uncertified_materials_register.csv",
            base / "material_certification_mode_register.json",
        ])
    if isinstance(result, MutableMapping):
        meta = result.setdefault("metadata", {})
        if isinstance(meta, MutableMapping):
            meta["material_certification_mode"] = mode
            meta["material_availability_blocks_engineering"] = False
            meta["available_alternative_material_count"] = availability.get("available_alternative_count", 0)
            meta["unavailable_material_count"] = availability.get("unavailable_material_count", 0)
            meta["uncertified_material_count"] = register.get("count", 0) if isinstance(register, Mapping) else 0
            meta["production_release"] = "LOCKED"
    return result


def _all_structural_requirements_eligible(workspace: Path, mode: str) -> bool:
    resolve_material_availability(workspace, mode)
    path = _selection_register(workspace)
    data = _read_json(path) if path else None
    selections = data.get("selections", []) if isinstance(data, Mapping) else []
    if not selections:
        return False
    if mode == MODE_UNCERTIFIED:
        build_uncertified_material_register(workspace)
    for selection in selections:
        if not isinstance(selection, Mapping):
            return False
        if _qualified(selection):
            continue
        available = _commercially_available(selection) and isinstance(selection.get("selected_product"), Mapping)
        if available and mode == MODE_CERTIFIED:
            # Strict checkbox remains strict for an actually selected available product.
            return False
        # Availability itself never blocks engineering. Both an uncertified available product in relaxed mode
        # and an unavailable design placeholder need an explicit required design class.
        if not resolve_required_design_class(workspace, selection):
            return False
    return True


def structural_certification_block_should_apply(local_context: Mapping[str, Any]) -> bool:
    mode = mode_from_context(local_context)
    workspace = resolve_workspace(local_context)
    return not (workspace and _all_structural_requirements_eligible(workspace, mode))


def cost_certification_block_should_apply(local_context: Mapping[str, Any]) -> bool:
    mode = mode_from_context(local_context)
    workspace = resolve_workspace(local_context)
    if not workspace:
        return True
    resolve_material_availability(workspace, mode)
    path = _selection_register(workspace)
    data = _read_json(path) if path else None
    selections = data.get("selections", []) if isinstance(data, Mapping) else []
    if not selections:
        return True
    if mode == MODE_UNCERTIFIED:
        build_uncertified_material_register(workspace)
        return False
    # In strict mode certification of a selected available product may still block the normal cost/engineering gate,
    # but unknown/unavailable supply by itself no longer blocks estimate generation.
    for selection in selections:
        if not isinstance(selection, Mapping):
            return True
        if _qualified(selection):
            continue
        if _commercially_available(selection) and isinstance(selection.get("selected_product"), Mapping):
            return True
    return False


def _availability_disclaimer_markdown(register: Mapping[str, Any]) -> str:
    lines = [
        "",
        "## MATERIAALBESCHIKBAARHEID EN ALTERNATIEVEN",
        "",
        "Onbekende of ontbrekende materiaalbeschikbaarheid blokkeert de ontwerpberekening niet.",
        "Phoenix zoekt eerst in de project-specifiek verworven lokale en internationale candidatevidence naar een",
        "beschikbaar alternatief uit dezelfde materiaalfamilie. Een gekozen alternatief vereist herberekening en traceerbare",
        "vastlegging. Wanneer geen aantoonbaar beschikbaar alternatief wordt gevonden, blijft het voorgeschreven materiaal",
        "als ontwerpplaceholder met de vereiste ontwerp-/sterkteklasse in de berekening staan. Dat is geen bewijs van leverbaarheid.",
        "Procurement/for-construction vrijgave blijft geblokkeerd totdat beschikbaarheid is opgelost.",
        "",
    ]
    unavailable = register.get("unavailable_materials", [])
    if unavailable:
        lines.extend(["### OP DIT MOMENT ALS ONBESCHIKBAAR / NIET-BEVESTIGD GEKWALIFICEERD", "", "| Materiaal | Vereiste ontwerpklasse | Ontwerpstatus |", "|---|---|---|"])
        for row in unavailable:
            if isinstance(row, Mapping):
                lines.append(f"| {row.get('material_family') or ''} | {row.get('required_design_class') or 'NOG TE BEPALEN'} | DESIGN CONTINUES / PROCUREMENT UNRESOLVED |")
        lines.append("")
    alternatives = register.get("available_alternatives", [])
    if alternatives:
        lines.extend(["### BESCHIKBARE ALTERNATIEVEN GESELECTEERD", "", "| Materiaal | Alternatief | Leverancier | Status |", "|---|---|---|---|"])
        for row in alternatives:
            if isinstance(row, Mapping):
                lines.append(f"| {row.get('material_family') or ''} | {row.get('selected_alternative_product_id') or ''} | {row.get('selected_alternative_supplier') or ''} | RECALCULATION REQUIRED |")
        lines.append("")
    return "\n".join(lines)


def _disclaimer_markdown(register: Mapping[str, Any]) -> str:
    lines = [
        "",
        "## ONGECERTIFICEERDE MATERIALEN EN AANGENOMEN ONTWERPEIGENSCHAPPEN",
        "",
        "Phoenix is voor deze projectrun uitgevoerd met **GECERTIFICEERD uitgeschakeld**.",
        "Lokaal aantoonbaar verkrijgbare producten waarvan voldoende productspecifieke certificatie ontbreekt,",
        "zijn niet als gecertificeerd aangemerkt. Voor de constructieve berekening wordt uitsluitend de",
        "vereiste ontwerp-/sterkteklasse als expliciete, niet-productgeverifieerde ontwerpaanname gebruikt.",
        "De berekening bewijst dus niet dat het aangeboden product deze eigenschappen bezit.",
        "Materiaalverificatie door certificaat, beproeving of beoordeling door de verantwoordelijke constructeur",
        "blijft vereist vóór vrijgave voor uitvoering.",
        "",
        "| Materiaal | Product / leverancier | Vereiste ontwerpklasse | Status |",
        "|---|---|---|---|",
    ]
    for row in register.get("materials", []):
        if not isinstance(row, Mapping):
            continue
        product = " / ".join(str(x) for x in (row.get("description"), row.get("supplier_name")) if x)
        lines.append(
            f"| {row.get('material_family') or ''} | {product} | {row.get('required_design_class') or 'NOG TE VERIFIËREN'} | ONGECERTIFICEERD |"
        )
    lines.extend(["", "**Vrijgave:** productie/for-construction blijft LOCKED tot materiaalverificatie.", ""])
    return "\n".join(lines)


def _annotate_structural_markdown(workspace: Path, register: Mapping[str, Any]) -> None:
    base = workspace / "results" / "session_adapters" / "structural_engineering"
    if not base.is_dir():
        return
    marker = "ONGECERTIFICEERDE MATERIALEN EN AANGENOMEN ONTWERPEIGENSCHAPPEN"
    section = _disclaimer_markdown(register)
    candidates = [
        path for path in base.rglob("*.md")
        if any(token in path.name.lower() for token in ("report", "rapport", "summary", "calculation"))
    ]
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8-sig")
            if marker not in text:
                path.write_text(text.rstrip() + "\n" + section, encoding="utf-8")
        except Exception:
            continue


def postprocess_structural_result(result: Any, *, args: Any = (), kwargs: Any = None) -> Any:
    context = {"args": args, "kwargs": kwargs or {}, "result": result}
    mode = mode_from_context(context)
    workspace = resolve_workspace(context)
    if not workspace:
        return result
    availability = resolve_material_availability(workspace, mode)
    uncertified = build_uncertified_material_register(workspace) if mode == MODE_UNCERTIFIED else {
        "count": 0, "materials": [], "unresolved_design_class_requirements": []
    }
    out_dir = workspace / "results" / "session_adapters" / "structural_engineering"
    availability_json = out_dir / "material_availability_design_status_report.json"
    availability_md = out_dir / "material_availability_design_status_report.md"
    availability_report = {
        "schema_version": "phoenix.material-availability-design-status-report/1.1",
        "project_id": workspace.name,
        "status": "ENGINEERING_CONTINUES_WITH_AVAILABILITY_RESOLUTION_OR_DESIGN_PLACEHOLDERS",
        "available_alternative_count": availability.get("available_alternative_count", 0),
        "unavailable_material_count": availability.get("unavailable_material_count", 0),
        "unresolved_design_class_requirements": availability.get("unresolved_design_class_requirements", []),
        "availability_blocks_engineering": False,
        "procurement_release": "LOCKED_IF_UNAVAILABLE_MATERIALS_PRESENT",
        "generated_utc": _now(),
        "available_alternatives": availability.get("available_alternatives", []),
        "unavailable_materials": availability.get("unavailable_materials", []),
    }
    _write_json(availability_json, availability_report)
    availability_md.parent.mkdir(parents=True, exist_ok=True)
    availability_md.write_text("# Constructieve materiaalbeschikbaarheid\n" + _availability_disclaimer_markdown(availability), encoding="utf-8")

    outputs = [availability_json, availability_md]
    if mode == MODE_UNCERTIFIED:
        report_json = out_dir / "uncertified_material_design_assumption_report.json"
        report_md = out_dir / "uncertified_material_design_assumption_report.md"
        report = {
            "schema_version": "phoenix.uncertified-material-design-assumption-report/1.1",
            "project_id": workspace.name,
            "status": "ENGINEERING_CONTINUES_WITH_EXPLICIT_UNCERTIFIED_DESIGN_ASSUMPTIONS",
            "uncertified_material_count": uncertified.get("count", 0),
            "unresolved_design_class_requirements": uncertified.get("unresolved_design_class_requirements", []),
            "calculation_interpretation": "Required material-class properties are design assumptions; actual offered product properties are not asserted as verified.",
            "material_verification_before_construction_release": "REQUIRED",
            "production_release": "LOCKED",
            "generated_utc": _now(),
            "materials": uncertified.get("materials", []),
        }
        _write_json(report_json, report)
        report_md.write_text("# Constructieve materiaalverificatie\n" + _disclaimer_markdown(uncertified), encoding="utf-8")
        outputs += [report_json, report_md]
        _annotate_structural_markdown(workspace, uncertified)

    # Append availability disclosure to existing structural markdown too.
    base = workspace / "results" / "session_adapters" / "structural_engineering"
    marker = "MATERIAALBESCHIKBAARHEID EN ALTERNATIEVEN"
    section = _availability_disclaimer_markdown(availability)
    if base.is_dir():
        for path in base.rglob("*.md"):
            if path in outputs:
                continue
            if any(token in path.name.lower() for token in ("report", "rapport", "summary", "calculation")):
                try:
                    current = path.read_text(encoding="utf-8-sig")
                    if marker not in current:
                        path.write_text(current.rstrip() + "\n" + section, encoding="utf-8")
                except Exception:
                    pass

    _append_outputs(result, outputs)
    if isinstance(result, MutableMapping):
        warnings = result.setdefault("warnings", [])
        if isinstance(warnings, list):
            if availability.get("unavailable_material_count", 0):
                warning = {
                    "reason": "MATERIAL_AVAILABILITY_UNRESOLVED_DESIGN_CONTINUES",
                    "message": "Geen aantoonbaar beschikbaar alternatief voor één of meer ontwerp-materialen; constructieve engineering gaat door met de vereiste ontwerpklasse als placeholder. Procurement/uitvoeringsvrijgave blijft geblokkeerd.",
                }
                if warning not in warnings:
                    warnings.append(warning)
            if mode == MODE_UNCERTIFIED and uncertified.get("count", 0):
                warning = {
                    "reason": "UNCERTIFIED_LOCAL_MATERIALS_USED_WITH_DESIGN_ASSUMPTIONS",
                    "message": "Beschikbare ongecertificeerde materialen zijn voor de berekening gekoppeld aan de vereiste ontwerpklasse als expliciete niet-productgeverifieerde aanname; verificatie is vereist vóór uitvoering.",
                }
                if warning not in warnings:
                    warnings.append(warning)
        meta = result.setdefault("metadata", {})
        if isinstance(meta, MutableMapping):
            meta["material_certification_mode"] = mode
            meta["material_availability_blocks_engineering"] = False
            meta["available_alternative_material_count"] = availability.get("available_alternative_count", 0)
            meta["unavailable_material_count"] = availability.get("unavailable_material_count", 0)
            meta["uncertified_material_count"] = uncertified.get("count", 0)
            meta["production_release"] = "LOCKED"
        result["production_release"] = "LOCKED"
    return result


def postprocess_cost_result(result: Any, *, args: Any = (), kwargs: Any = None) -> Any:
    context = {"args": args, "kwargs": kwargs or {}, "result": result}
    mode = mode_from_context(context)
    workspace = resolve_workspace(context)
    if not workspace:
        return result
    availability = resolve_material_availability(workspace, mode)
    uncertified = build_uncertified_material_register(workspace) if mode == MODE_UNCERTIFIED else {"count": 0}
    unavailable = availability.get("unavailable_materials", [])
    unpriced = [row for row in unavailable if isinstance(row, Mapping) and row.get("unit_price_if_present_not_confirmed_by_availability") in (None, "")]
    if isinstance(result, MutableMapping):
        meta = result.setdefault("metadata", {})
        if isinstance(meta, MutableMapping):
            meta["material_certification_mode"] = mode
            meta["material_availability_blocks_cost_estimate_generation"] = False
            meta["uncertified_local_material_price_policy"] = "INCLUDE_CONFIRMED_PRICE" if mode == MODE_UNCERTIFIED else "STRICT_CERTIFICATION_FOR_AVAILABLE_SELECTED_PRODUCTS"
            meta["uncertified_material_count"] = uncertified.get("count", 0)
            meta["available_alternative_material_count"] = availability.get("available_alternative_count", 0)
            meta["unavailable_material_count"] = availability.get("unavailable_material_count", 0)
            meta["unavailable_material_unpriced_count"] = len(unpriced)
            meta["material_cost_completeness"] = "PARTIAL_UNRESOLVED_MATERIAL_PRICES" if unpriced else "NO_UNPRICED_UNAVAILABLE_MATERIALS"
        if unpriced:
            warnings = result.setdefault("warnings", [])
            warning = {
                "reason": "UNAVAILABLE_MATERIAL_PRICE_UNRESOLVED",
                "message": "Kostenraming is gegenereerd, maar één of meer op dit moment onbeschikbare materialen hebben geen bevestigde actuele prijs. Phoenix verzint geen prijs; deze posten blijven expliciet prijs-onopgelost.",
            }
            if isinstance(warnings, list) and warning not in warnings:
                warnings.append(warning)
    return result

