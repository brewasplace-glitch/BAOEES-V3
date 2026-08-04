from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo(ctx: dict[str, Any]) -> Path:
    for key in ("repository", "repo", "repo_root"):
        value = ctx.get(key)
        if value:
            return Path(value).resolve()
    return Path.cwd().resolve()


def _workspace(ctx: dict[str, Any]) -> Path:
    value = ctx.get("workspace")
    if value:
        return Path(value).resolve()
    project_id = str(ctx.get("project_id") or (ctx.get("session") or {}).get("project_id") or "UNKNOWN_PROJECT")
    return (_repo(ctx) / "projects" / "runtime" / project_id).resolve()


def _country_candidates(ctx: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    objects = [
        ctx,
        ctx.get("project_context") or {},
        ctx.get("market_context") or {},
        ctx.get("geography") or {},
        (ctx.get("session") or {}).get("project_context") or {},
        (ctx.get("session") or {}).get("geography") or {},
    ]
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        for key in ("country_code", "country"):
            value = obj.get(key)
            if value:
                candidates.append(str(value).strip().upper())
        geo = obj.get("geography")
        if isinstance(geo, dict):
            for key in ("country_code", "country"):
                value = geo.get(key)
                if value:
                    candidates.append(str(value).strip().upper())
    # Project-context files are authoritative enough to determine applicability, but not normative law.
    ws = _workspace(ctx)
    for rel in (
        "project_manifest.json",
        "digital_twin/project_state.json",
        "orchestration/project_context.json",
        "results/session_adapters/architecture/project_context.json",
    ):
        path = ws / rel
        if path.exists():
            try:
                data = _read_json(path)
            except Exception:
                continue
            stack = [data]
            while stack:
                cur = stack.pop()
                if isinstance(cur, dict):
                    for k, v in cur.items():
                        if k == "country_code" and v:
                            candidates.append(str(v).strip().upper())
                        elif isinstance(v, (dict, list)):
                            stack.append(v)
                elif isinstance(cur, list):
                    stack.extend(cur)
    return candidates


def is_suriname_building_context(ctx: dict[str, Any]) -> bool:
    countries = set(_country_candidates(ctx))
    if not ({"SR", "SURINAME"} & countries):
        return False
    ptype = str(
        ctx.get("project_type")
        or (ctx.get("session") or {}).get("project_type")
        or (ctx.get("project_context") or {}).get("project_type")
        or "BOUW"
    ).upper()
    return ptype in {"BOUW", "BUILDING", "ARCHITECTURE", "WONING", "RESIDENTIAL"}


def write_suriname_structural_knowledge_register(ctx: dict[str, Any]) -> Path | None:
    if not is_suriname_building_context(ctx):
        return None
    repo = _repo(ctx)
    ws = _workspace(ctx)
    policy = _read_json(repo / "configs/phoenix/suriname_structural_knowledge_policy_v1_0.json")
    evidence = _read_json(repo / "configs/phoenix/suriname_structural_reference_evidence_catalog_v1_0.json")
    out = ws / "results" / "knowledge"
    out.mkdir(parents=True, exist_ok=True)
    target = out / "suriname_structural_knowledge_register.json"
    register = {
        "schema_version": "phoenix.suriname-structural-knowledge-register/1.0",
        "project_id": str(ctx.get("project_id") or (ctx.get("session") or {}).get("project_id") or ws.name),
        "country_code": "SR",
        "status": "REFERENCE_KNOWLEDGE_AVAILABLE_REVIEW_REQUIRED",
        "knowledge_layers": policy["knowledge_layers"],
        "suriname_interim_load_policy": policy["suriname_interim_load_policy"],
        "reference_evidence": evidence["references"],
        "normative_code_basis_auto_approved": False,
        "project_specific_reference_values_promoted_to_defaults": False,
        "professional_review_required": True,
        "production_release": "LOCKED_PENDING_BASELINE_AND_PROFESSIONAL_REVIEW",
    }
    target.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
