from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phoenix.autonomy.suriname_structural_knowledge import is_suriname_building_context
from phoenix.autonomy.deliverable_evidence_resolver import build_minimum_deliverable_manifest


VALID = {
    "GENERATED_AND_VALIDATED",
    "NOT_APPLICABLE_WITH_REASON",
    "BLOCKED_WITH_EXPLICIT_REASON",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo(ctx: dict[str, Any]) -> Path:
    for key in ("repository", "repo", "repo_root"):
        if ctx.get(key):
            return Path(ctx[key]).resolve()
    return Path.cwd().resolve()


def _workspace(ctx: dict[str, Any]) -> Path:
    if ctx.get("workspace"):
        return Path(ctx["workspace"]).resolve()
    project_id = str(ctx.get("project_id") or (ctx.get("session") or {}).get("project_id") or "UNKNOWN_PROJECT")
    return (_repo(ctx) / "projects" / "runtime" / project_id).resolve()


def _load_explicit_manifest(ws: Path) -> dict[str, Any]:
    candidates = [
        ws / "orchestration" / "minimum_deliverable_manifest.json",
        ws / "results" / "minimum_deliverable_manifest.json",
        ws / "minimum_deliverable_manifest.json",
    ]
    for path in candidates:
        if path.exists():
            data = _read_json(path)
            if isinstance(data, dict):
                data["_source_path"] = str(path)
                return data
    return {"items": [], "_source_path": None}


def _explicit_item_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in manifest.get("items", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        result[str(item["id"])] = item
    return result


def _evaluate_item(spec: dict[str, Any], explicit: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item_id = spec["id"]
    supplied = explicit.get(item_id)
    if supplied:
        status = str(supplied.get("status") or "").upper()
        reason = str(supplied.get("reason") or "").strip()
        evidence = supplied.get("evidence") or supplied.get("artifacts") or []
        if status not in VALID:
            return {
                "id": item_id,
                "label": spec["label"],
                "status": "BLOCKED_WITH_EXPLICIT_REASON",
                "reason": "INVALID_EXPLICIT_BASELINE_STATUS",
                "detail": f"Unsupported status: {status or '<empty>'}",
            }
        if status == "NOT_APPLICABLE_WITH_REASON" and not reason:
            return {
                "id": item_id,
                "label": spec["label"],
                "status": "BLOCKED_WITH_EXPLICIT_REASON",
                "reason": "NOT_APPLICABLE_REASON_REQUIRED",
            }
        if status == "GENERATED_AND_VALIDATED" and not evidence:
            return {
                "id": item_id,
                "label": spec["label"],
                "status": "BLOCKED_WITH_EXPLICIT_REASON",
                "reason": "VALIDATED_EVIDENCE_REFERENCE_REQUIRED",
            }
        return {
            "id": item_id,
            "label": spec["label"],
            "status": status,
            "reason": reason or None,
            "evidence": evidence,
        }

    required = bool(spec.get("required", False))
    conditional = spec.get("conditional")
    if required:
        reason = "REQUIRED_BASELINE_DELIVERABLE_NOT_EXPLICITLY_VALIDATED"
    elif conditional:
        reason = f"APPLICABILITY_DECISION_REQUIRED:{conditional}"
    else:
        reason = "BASELINE_STATUS_REQUIRED"
    return {
        "id": item_id,
        "label": spec["label"],
        "status": "BLOCKED_WITH_EXPLICIT_REASON",
        "reason": reason,
    }


def evaluate_and_write_baseline(ctx: dict[str, Any]) -> dict[str, Any] | None:
    if not is_suriname_building_context(ctx):
        return None
    repo = _repo(ctx)
    ws = _workspace(ctx)
    baseline = _read_json(repo / "configs/phoenix/building_minimum_deliverable_baseline_v1_0.json")
    # Preserve a deliberately supplied project manifest. Only when no explicit
    # manifest exists may Phoenix resolve registered artifacts automatically.
    # This keeps user/project decisions authoritative while eliminating manual
    # duplicate evidence entry for ordinary autonomous runs.
    explicit_manifest = _load_explicit_manifest(ws)
    if not explicit_manifest.get("_source_path"):
        build_minimum_deliverable_manifest(ctx)
        explicit_manifest = _load_explicit_manifest(ws)
    explicit = _explicit_item_map(explicit_manifest)

    specs = []
    specs.extend(baseline["drawing_baseline"]["items"])
    specs.extend(baseline["structural_report_baseline"])
    items = [_evaluate_item(spec, explicit) for spec in specs]
    blockers = [item for item in items if item["status"] == "BLOCKED_WITH_EXPLICIT_REASON"]
    release_ready = not blockers

    out_dir = ws / "results" / "session_adapters" / "closure"
    out_dir.mkdir(parents=True, exist_ok=True)
    register_path = out_dir / "minimum_deliverable_baseline_register.json"
    overlay_path = out_dir / "minimum_deliverable_release_gate_overlay.json"

    register = {
        "schema_version": "phoenix.minimum-deliverable-baseline-register/1.0",
        "project_id": str(ctx.get("project_id") or (ctx.get("session") or {}).get("project_id") or ws.name),
        "baseline_id": baseline["baseline_id"],
        "country_code": "SR",
        "explicit_manifest_source": explicit_manifest.get("_source_path"),
        "status": "PASSED" if release_ready else "BLOCKED",
        "blocker_count": len(blockers),
        "items": items,
        "automatic_professional_approval": False,
        "professional_review_required": True,
        "production_release": "LOCKED" if not release_ready else "READY_FOR_PROFESSIONAL_REVIEW",
    }
    register_path.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    overlay = {
        "schema_version": "phoenix.minimum-deliverable-release-gate-overlay/1.0",
        "project_id": register["project_id"],
        "gate_id": "SURINAME_MINIMUM_DELIVERABLE_BASELINE_V1_0",
        "gate_status": "BLOCKED" if not release_ready else "READY_FOR_PROFESSIONAL_REVIEW",
        "release_ready": False,  # professional review remains mandatory even if baseline content is complete
        "baseline_content_complete": release_ready,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
    }
    overlay_path.write_text(json.dumps(overlay, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return register
