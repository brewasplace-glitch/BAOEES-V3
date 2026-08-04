"""Minimum-deliverable evidence resolver for Suriname building projects."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .desired_output_evidence import validate_desired_output_evidence

VERSION = "1.0.0"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _repo(ctx: dict[str, Any]) -> Path:
    for key in ("repository", "repo", "repo_root"):
        if ctx.get(key):
            return Path(ctx[key]).resolve()
    return Path.cwd().resolve()


def _workspace(ctx: dict[str, Any]) -> Path:
    if ctx.get("workspace"):
        return Path(ctx["workspace"]).resolve()
    return _repo(ctx) / "projects" / "runtime" / str(ctx.get("project_id") or "UNKNOWN_PROJECT")


def _adapter_state(ws: Path) -> dict[str, Any]:
    return _read(ws / "orchestration" / "adapter_state.json")


def _existing(paths: list[Path], repo: Path) -> list[str]:
    result = []
    for p in paths:
        if p.is_file() and p.stat().st_size > 0:
            try:
                result.append(p.resolve().relative_to(repo.resolve()).as_posix())
            except ValueError:
                result.append(str(p.resolve()))
    return result


def _find(ws: Path, tokens: tuple[str, ...], suffixes: tuple[str, ...] = ()) -> list[Path]:
    result = []
    if not ws.exists():
        return result
    for p in ws.rglob("*"):
        if not p.is_file() or p.stat().st_size <= 0:
            continue
        if suffixes and p.suffix.casefold() not in suffixes:
            continue
        n = p.name.casefold()
        if any(t in n for t in tokens):
            result.append(p)
    return sorted(set(result))


def _entry(item_id: str, label: str, status: str, reason: str | None, evidence: list[str]) -> dict[str, Any]:
    value = {"id": item_id, "label": label, "status": status}
    if reason:
        value["reason"] = reason
    if evidence:
        value["evidence"] = evidence
    return value


def build_minimum_deliverable_manifest(ctx: dict[str, Any]) -> dict[str, Any]:
    repo = _repo(ctx)
    ws = _workspace(ctx)
    baseline = _read(repo / "configs" / "phoenix" / "building_minimum_deliverable_baseline_v1_0.json")
    state = _adapter_state(ws)
    capabilities = state.get("capabilities") if isinstance(state, dict) else {}
    capabilities = capabilities if isinstance(capabilities, dict) else {}

    labels: dict[str, str] = {}
    for spec in list((baseline.get("drawing_baseline") or {}).get("items") or []) + list(baseline.get("structural_report_baseline") or []):
        if isinstance(spec, dict) and spec.get("id"):
            labels[str(spec["id"])] = str(spec.get("label") or spec["id"])

    items: list[dict[str, Any]] = []

    # Direct desired-output evidence mapping.
    output_map = {
        "B01_FLOOR_PLAN": "floor_plans",
        "B02_FOUNDATION_PLAN": "foundation_drawings",
        "B04_B05_FACADES": "facades",
        "B07_SECTIONS": "sections",
        "S01_SITE_PLAN": "site_plan",
    }
    for item_id, oid in output_map.items():
        check = validate_desired_output_evidence(repository=repo, workspace=ws, output_id=oid, capability_states=capabilities)
        if check["status"] == "PASSED":
            items.append(_entry(item_id, labels[item_id], "GENERATED_AND_VALIDATED", None, list(check.get("evidence") or [])))
        else:
            items.append(_entry(item_id, labels[item_id], "BLOCKED_WITH_EXPLICIT_REASON", str(check.get("reason") or "DELIVERABLE_EVIDENCE_REQUIRED"), list(check.get("evidence") or [])))

    # Building services / architectural items not yet represented by a dedicated
    # producer remain explicit blockers instead of false passes.
    drawing_search = {
        "B03_SEWERAGE_PLAN": (("sewer", "riolering", "rwa"), (".pdf", ".svg", ".dxf", ".dwg")),
        "B06_ROOF_PLAN": (("roof_plan", "dakplan", "kapplan"), (".pdf", ".svg", ".dxf", ".dwg")),
        "B08_DETAILS": (("detail",), (".pdf", ".svg", ".dxf", ".dwg")),
        "B10_OPENING_SCHEDULE": (("opening_schedule", "kozijnen", "raamstaat", "deurstaat"), (".pdf", ".xlsx", ".csv", ".json")),
        "B11_INFORMATION_FINISHES": (("finishes", "afwerking", "information_plan"), (".pdf", ".xlsx", ".json")),
        "B12_WATER_PLAN": (("water_plan", "waterinstallatie"), (".pdf", ".svg", ".dxf", ".dwg")),
        "B14_ELECTRICAL_PLAN": (("electrical", "elektra"), (".pdf", ".svg", ".dxf", ".dwg")),
    }
    for item_id, (tokens, suffixes) in drawing_search.items():
        evidence = _existing(_find(ws, tokens, suffixes), repo)
        items.append(_entry(item_id, labels[item_id], "GENERATED_AND_VALIDATED" if evidence else "BLOCKED_WITH_EXPLICIT_REASON", None if evidence else "DEDICATED_DELIVERABLE_ENGINE_OR_VALIDATED_ARTIFACT_REQUIRED", evidence))

    for item_id, token, conditional in (
        ("B09_SEPTIC_TANK", "septic", "on_site_wastewater"),
        ("B13_HVAC_PLAN", "hvac", "mechanical_cooling"),
    ):
        evidence = _existing(_find(ws, (token, "airco" if token == "hvac" else token), (".pdf", ".svg", ".dxf", ".dwg")), repo)
        if evidence:
            items.append(_entry(item_id, labels[item_id], "GENERATED_AND_VALIDATED", None, evidence))
        else:
            items.append(_entry(item_id, labels[item_id], "BLOCKED_WITH_EXPLICIT_REASON", f"APPLICABILITY_DECISION_REQUIRED:{conditional}", []))

    structural_root = ws / "results" / "session_adapters" / "structural_engineering"
    arch_root = ws / "results" / "session_adapters" / "architecture"
    closure_root = ws / "results" / "session_adapters" / "closure"

    structural_candidates = _read(structural_root / "v8_0_structural_derivation" / "model" / "structural_candidate_model.json")
    stage_register = _read(structural_root / "validated_v8_1_to_v8_12" / "stage_register.json")
    material_path = arch_root / "structural_material_selection_register.json"
    if not material_path.is_file():
        material_path = arch_root / "local_material_selection_register.json"
    material_register = _read(material_path)
    load_register = _read(structural_root / "validated_v8_1_to_v8_12" / "v8_2" / "structural_action_load_source_register.json")

    structural_rules = {
        "STR_PROJECT_SCOPE": [arch_root / "structural_project_profile.json", structural_root / "structural_v8_chain_manifest.json"],
        "STR_CODE_BASIS": [structural_root / "suriname_structural_load_basis_register.json", structural_root / "validated_v8_1_to_v8_12" / "v8_2" / "structural_action_load_source_register.json"],
        "STR_LOADS": [structural_root / "validated_v8_1_to_v8_12" / "v8_2" / "action_load_model.json"],
        "STR_MODEL": [structural_root / "validated_v8_1_to_v8_12" / "v8_1" / "analytical_model.json"],
        "STR_UGT_BGT": [structural_root / "validated_v8_1_to_v8_12" / "v8_4" / "analysis_validation.json", structural_root / "validated_v8_1_to_v8_12" / "v8_5" / "member_verification.json"],
        "STR_ROOF_STRUCTURE": [structural_root / "validated_v8_1_to_v8_12" / "v8_5" / "member_verification.json"],
        "STR_FOUNDATION": [structural_root / "validated_v8_1_to_v8_12" / "v8_9" / "foundation_design_report.json"],
        "STR_CONNECTIONS": [structural_root / "validated_v8_1_to_v8_12" / "v8_7" / "connection_report.json"],
        "STR_DRAWINGS": [structural_root / "validated_v8_1_to_v8_12" / "v8_10" / "engineering_package_qaqc.json"],
        "STR_QA_REVIEW": [closure_root / "qaqc_release_gate.json", structural_root / "validated_v8_1_to_v8_12" / "v8_11" / "engineering_review_release.json"],
    }
    for item_id, paths in structural_rules.items():
        evidence = _existing(paths, repo)
        complete = len(evidence) == len(paths)
        items.append(_entry(item_id, labels[item_id], "GENERATED_AND_VALIDATED" if complete else "BLOCKED_WITH_EXPLICIT_REASON", None if complete else "STRUCTURAL_STAGE_EVIDENCE_REQUIRED", evidence))

    material_evidence = _existing([material_path], repo)
    material_ok = bool(material_register.get("all_structural_requirements_engineering_qualified"))
    items.append(_entry("STR_MATERIALS", labels["STR_MATERIALS"], "GENERATED_AND_VALIDATED" if material_ok and material_evidence else "BLOCKED_WITH_EXPLICIT_REASON", None if material_ok else "LOCAL_STRUCTURAL_PRODUCT_TECHNICAL_EVIDENCE_REQUIRED", material_evidence))

    def has_collection(*names: str) -> bool:
        for name in names:
            value = structural_candidates.get(name)
            if isinstance(value, list) and value:
                return True
        return False

    member_verify = structural_root / "validated_v8_1_to_v8_12" / "v8_5" / "member_verification.json"
    member_evidence = _existing([member_verify], repo)
    for item_id, present, cond in (
        ("STR_SLABS", has_collection("slabs", "slab_panels"), "slabs_present"),
        ("STR_BEAMS", has_collection("beams"), "beams_present"),
        ("STR_COLUMNS", has_collection("columns"), "columns_present"),
    ):
        if not present:
            items.append(_entry(item_id, labels[item_id], "NOT_APPLICABLE_WITH_REASON", f"NO_{cond.upper()}_IN_STRUCTURAL_CANDIDATE_MODEL", _existing([structural_root / "v8_0_structural_derivation" / "model" / "structural_candidate_model.json"], repo)))
        elif member_evidence:
            items.append(_entry(item_id, labels[item_id], "GENERATED_AND_VALIDATED", None, member_evidence))
        else:
            items.append(_entry(item_id, labels[item_id], "BLOCKED_WITH_EXPLICIT_REASON", "MEMBER_VERIFICATION_EVIDENCE_REQUIRED", []))

    manifest_path = ws / "orchestration" / "minimum_deliverable_manifest.json"
    register_path = closure_root / "deliverable_evidence_resolver_register.json"
    blocker_count = sum(1 for x in items if x["status"] == "BLOCKED_WITH_EXPLICIT_REASON")
    manifest = {
        "schema_version": "phoenix.minimum-deliverable-manifest/1.0",
        "resolver_version": VERSION,
        "project_id": str(ctx.get("project_id") or ws.name),
        "items": items,
        "blocker_count": blocker_count,
        "evidence_is_professional_approval": False,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
    }
    _write(manifest_path, manifest)
    _write(register_path, {
        "schema_version": "phoenix.deliverable-evidence-resolver-register/1.0",
        "resolver_version": VERSION,
        "project_id": manifest["project_id"],
        "status": "PASSED" if blocker_count == 0 else "BLOCKED",
        "blocker_count": blocker_count,
        "manifest_reference": manifest_path.resolve().relative_to(repo.resolve()).as_posix(),
        "item_count": len(items),
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
    })
    return manifest
