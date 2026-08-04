"""Phoenix Suriname Structural Load Basis v1.0.

Creates a project-specific interim structural action/load source for autonomous
Suriname low-rise residential building projects when the explicit user-approved
Suriname interim policy applies. The generated source is intentionally marked as
engineering-policy evidence, not verified law, and never grants professional
approval or production release.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
BASIS_ID = "SR-INTERIM-LOW-RISE-RESIDENTIAL-LOAD-BASIS-1.0"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _context(ctx: dict[str, Any], project_context_ref: str | None) -> dict[str, Any]:
    repository = Path(ctx["repository"]).resolve()
    if project_context_ref:
        p = (repository / project_context_ref).resolve()
        if p.is_file():
            try:
                return _read(p)
            except Exception:
                pass
    return {}


def _is_residential_low_rise(ctx: dict[str, Any], project_context: dict[str, Any]) -> bool:
    session = ctx.get("session") or {}
    brief = str(session.get("brief") or "").casefold()
    project_type = str(session.get("project_type") or "").upper().strip()
    if project_type not in {"BOUW", "BUILDING"}:
        return False
    residential_tokens = ("woning", "woonhuis", "residential", "house", "vrijstaande")
    if not any(token in brief for token in residential_tokens):
        return False
    storeys = None
    facts = project_context.get("facts") if isinstance(project_context, dict) else None
    if isinstance(facts, dict):
        storeys = facts.get("storey_count") or facts.get("storeys")
    if storeys is not None:
        try:
            return int(storeys) <= 3
        except (TypeError, ValueError):
            pass
    return True


def ensure_suriname_structural_load_basis(
    ctx: dict[str, Any],
    *,
    project_context_ref: str | None,
) -> dict[str, Any]:
    repository = Path(ctx["repository"]).resolve()
    workspace = Path(ctx["workspace"]).resolve()
    output_dir = Path(ctx["output_dir"]).resolve()
    project_id = str(ctx.get("project_id") or "UNKNOWN_PROJECT")
    project_context = _context(ctx, project_context_ref)
    facts = project_context.get("facts") if isinstance(project_context, dict) else {}
    facts = facts if isinstance(facts, dict) else {}
    country = str(facts.get("country_code") or "").upper().strip()
    region = facts.get("region")
    municipality = facts.get("municipality")

    register_path = output_dir / "suriname_structural_load_basis_register.json"
    result: dict[str, Any] = {
        "schema_version": "phoenix.suriname-structural-load-basis-register/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "country_code": country or None,
        "region_name": region,
        "municipality": municipality,
        "status": "NOT_APPLICABLE",
        "source_reference": None,
        "policy_basis": "USER_APPROVED_ENGINEERING_POLICY_REQUIRING_PROFESSIONAL_REVIEW",
        "verified_as_current_law": False,
        "professional_review_required": True,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
        "warnings": [],
    }

    if country != "SR":
        _write(register_path, result)
        return {"status": "NOT_APPLICABLE", "register": _repo_ref(register_path, repository), "source": None}

    if not _is_residential_low_rise(ctx, project_context):
        result.update({
            "status": "BLOCKED",
            "reason": "SURINAME_INTERIM_LOAD_PROFILE_SCOPE_REVIEW_REQUIRED",
            "message": "De huidige Suriname interim-loadbasis is alleen geautoriseerd voor laagbouw-woningprojecten; voor andere gebouwtypen is projectspecifieke load-basis evidence vereist.",
        })
        _write(register_path, result)
        return {"status": "BLOCKED", "register": _repo_ref(register_path, repository), "source": None}

    today = date.today()
    source_dir = workspace / "sources" / "structural_action_load"
    source_path = source_dir / "000_SR_INTERIM_LOW_RISE_RESIDENTIAL_LOAD_BASIS_v1_0.json"

    # The numeric residential floor action and reference wind pressure are taken
    # from the user-provided Suriname structural practice report already catalogued
    # by the Structural Knowledge Baseline. They are scoped here as an interim
    # Paramaribo low-rise residential engineering-policy candidate only, never as
    # universal Suriname defaults or verified law.
    action_input = {
        "basis": "SR_INTERIM_USER_APPROVED_DUTCH_EUROCODE_STYLE_LOW_RISE_RESIDENTIAL_CANDIDATE",
        "unit_system": {"length": "m", "force": "kN", "moment": "kNm", "stress": "kPa", "mass": "kg"},
        "actions": [
            {
                "id": "SR-G-SW", "case_id": "LC-G", "case_name": "Permanent self weight",
                "category": "permanent", "kind": "self_weight", "direction": "GRAVITY",
                "factor": 1.0, "target": {"all_elements": True},
            },
            {
                "id": "SR-Q-RES-FLOOR", "case_id": "LC-Q", "case_name": "Residential imposed floor action",
                "category": "variable", "kind": "area", "direction": "GLOBAL_Z",
                "magnitude": -1.75, "factor": 1.0, "target": {"all_shells": True},
                "value_basis": "SR-REF-STRUCTUURPLUS-2026 residential reference evidence",
            },
            {
                "id": "SR-W-XP", "case_id": "LC-WXP", "case_name": "Reference wind +X",
                "category": "wind", "kind": "line", "direction": "GLOBAL_X",
                "magnitude": 0.45, "factor": 1.0, "target": {"all_members": True},
                "value_basis": "SR-REF-STRUCTUURPLUS-2026 reference wind pressure",
            },
            {
                "id": "SR-W-XN", "case_id": "LC-WXN", "case_name": "Reference wind -X",
                "category": "wind", "kind": "line", "direction": "GLOBAL_X",
                "magnitude": -0.45, "factor": 1.0, "target": {"all_members": True},
                "value_basis": "SR-REF-STRUCTUURPLUS-2026 reference wind pressure",
            },
            {
                "id": "SR-W-YP", "case_id": "LC-WYP", "case_name": "Reference wind +Y",
                "category": "wind", "kind": "line", "direction": "GLOBAL_Y",
                "magnitude": 0.45, "factor": 1.0, "target": {"all_members": True},
                "value_basis": "SR-REF-STRUCTUURPLUS-2026 reference wind pressure",
            },
            {
                "id": "SR-W-YN", "case_id": "LC-WYN", "case_name": "Reference wind -Y",
                "category": "wind", "kind": "line", "direction": "GLOBAL_Y",
                "magnitude": -0.45, "factor": 1.0, "target": {"all_members": True},
                "value_basis": "SR-REF-STRUCTUURPLUS-2026 reference wind pressure",
            },
        ],
        "combinations": [],
        "snow_action": {
            "included": False,
            "basis": "USER_APPROVED_SURINAME_INTERIM_POLICY",
            "override_if_project_evidence_requires": True,
        },
    }

    for case_id in ("LC-Q", "LC-WXP", "LC-WXN", "LC-WYP", "LC-WYN"):
        action_input["combinations"].append({
            "id": f"SR-ULS-{case_id}",
            "name": f"Interim ULS G + {case_id}",
            "limit_state": "ULS",
            "basis": "USER_APPROVED_DUTCH_EUROCODE_STYLE_INTERIM_POLICY",
            "terms": [
                {"case_id": "LC-G", "coefficient": 1.20},
                {"case_id": case_id, "coefficient": 1.50},
            ],
        })
        action_input["combinations"].append({
            "id": f"SR-SLS-{case_id}",
            "name": f"Interim SLS G + {case_id}",
            "limit_state": "SLS",
            "basis": "USER_APPROVED_DUTCH_EUROCODE_STYLE_INTERIM_POLICY",
            "terms": [
                {"case_id": "LC-G", "coefficient": 1.00},
                {"case_id": case_id, "coefficient": 1.00},
            ],
        })

    source = {
        "metadata": {
            "basis_id": BASIS_ID,
            "country_code": "SR",
            "region_name": region,
            "municipality": municipality,
            "source_name": "Project Phoenix Suriname Interim Structural Load Policy v1.0",
            "source_type": "USER_APPROVED_ENGINEERING_POLICY_PLUS_REFERENCE_PRACTICE_EVIDENCE",
            "effective_date": today.isoformat(),
            "valid_until": (today + timedelta(days=30)).isoformat(),
            "status": "ACTIVE",
            "verified_as_current_law": False,
            "professional_review_required": True,
            "reference_evidence": [
                "SR-REF-STRUCTUURPLUS-2026",
                "SR-REF-NEA-ARCHI-2022",
                "configs/phoenix/suriname_structural_knowledge_policy_v1_0.json",
            ],
            "project_specific_values_promoted_to_global_defaults": False,
            "scope": "AUTONOMOUS_SR_LOW_RISE_RESIDENTIAL_CANDIDATE_ONLY",
        },
        "action_load_input": action_input,
    }
    _write(source_path, source)

    result.update({
        "status": "PASSED",
        "source_reference": _repo_ref(source_path, repository),
        "basis_id": BASIS_ID,
        "snow_action_included": False,
        "interim_reference_values": {
            "residential_imposed_floor_action_kN_m2": 1.75,
            "reference_wind_pressure_kN_m2": 0.45,
            "uls_permanent_factor": 1.20,
            "uls_variable_factor": 1.50,
        },
        "warnings": [
            "Interim load basis is an engineering-policy candidate and is not represented as verified Suriname law.",
            "Reference load magnitudes are scoped to the autonomous Paramaribo low-rise residential PAT profile and require professional review before release.",
        ],
    })
    _write(register_path, result)
    return {
        "status": "PASSED",
        "register": _repo_ref(register_path, repository),
        "source": _repo_ref(source_path, repository),
    }
