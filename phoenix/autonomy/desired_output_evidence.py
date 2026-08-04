"""Desired-output evidence validation for Project Phoenix autonomous sessions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "1.0.0"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _existing(repository: Path, refs: list[str]) -> list[str]:
    out = []
    for ref in refs:
        p = (repository / ref).resolve() if not Path(ref).is_absolute() else Path(ref)
        if p.is_file() and p.stat().st_size > 0:
            out.append(ref)
    return out


def _cap_outputs(capability_states: dict[str, Any], cap: str) -> list[str]:
    value = capability_states.get(cap) or {}
    return [str(x) for x in value.get("outputs", [])]


def _find(workspace: Path, patterns: tuple[str, ...], suffixes: tuple[str, ...] = ()) -> list[Path]:
    result = []
    if not workspace.exists():
        return result
    for p in workspace.rglob("*"):
        if not p.is_file() or p.stat().st_size <= 0:
            continue
        name = p.name.casefold()
        if suffixes and p.suffix.casefold() not in suffixes:
            continue
        if any(token in name for token in patterns):
            result.append(p)
    return sorted(set(result))


def _refs(paths: list[Path], repository: Path) -> list[str]:
    out = []
    for p in paths:
        try:
            out.append(p.resolve().relative_to(repository.resolve()).as_posix())
        except ValueError:
            out.append(str(p.resolve()))
    return out


def validate_desired_output_evidence(
    *,
    repository: Path,
    workspace: Path,
    output_id: str,
    capability_states: dict[str, Any],
) -> dict[str, Any]:
    repository = repository.resolve()
    workspace = workspace.resolve()
    oid = str(output_id)
    evidence: list[str] = []
    status = "BLOCKED"
    reason = "DESIRED_OUTPUT_ARTIFACT_REQUIRED"
    stage = "ARTIFACT_EVIDENCE_REQUIRED"

    arch = _cap_outputs(capability_states, "architecture")
    dt = _cap_outputs(capability_states, "digital_twin")
    structural = _cap_outputs(capability_states, "structural_engineering")
    permit = _cap_outputs(capability_states, "permit")
    cost = _cap_outputs(capability_states, "cost_planning")
    reporting = _cap_outputs(capability_states, "reporting")
    closure = _cap_outputs(capability_states, "closure")

    if oid == "reports":
        evidence = _existing(repository, [x for x in reporting if x.endswith((".md", ".json", ".pdf", ".docx"))])
    elif oid == "calculations":
        evidence = _existing(repository, [x for x in structural if any(k in x for k in ("analysis_validation", "member_verification", "engineering_package_qaqc", "foundation_design_report"))])
    elif oid == "permit_dossier":
        evidence = _existing(repository, [x for x in permit if x.endswith(("permit_scope.json", "permit_checklist.json"))])
        if len(evidence) < 2:
            evidence = []
    elif oid == "cost_estimate":
        evidence = _existing(repository, [x for x in cost if x.endswith("local_cost_calculation.json")])
    elif oid == "site_plan":
        evidence = _existing(repository, [x for x in arch if "/drawings/site_plan." in x])
    elif oid == "floor_plans":
        evidence = _existing(repository, [x for x in arch if "/drawings/floor_plan_" in x])
    elif oid == "facades":
        evidence = _existing(repository, [x for x in arch if "/drawings/elevation_" in x])
        if len([x for x in evidence if x.endswith(".svg")]) < 4:
            evidence = []
    elif oid == "sections":
        evidence = _existing(repository, [x for x in arch if "/drawings/section_" in x])
        if len([x for x in evidence if x.endswith(".svg")]) < 2:
            evidence = []
    elif oid == "digital_twin_output":
        evidence = _existing(repository, [x for x in dt if x.endswith("central_project_digital_twin.json")])
    elif oid == "structural_analysis":
        evidence = _existing(repository, [x for x in structural if any(k in x for k in ("analysis_validation.json", "member_verification.json"))])
    elif oid == "viewer_3d":
        evidence = _refs(_find(workspace, ("viewer", "3d_viewer"), (".html", ".gltf", ".glb")), repository)
        reason = "REAL_3D_VIEWER_ARTIFACT_REQUIRED"
    elif oid == "qaqc_output":
        evidence = _existing(repository, [x for x in closure if x.endswith("qaqc_release_gate.json")])
        if evidence:
            gate = _read((repository / evidence[0]).resolve())
            if str(gate.get("qaqc_status") or "").upper() == "BLOCKED":
                return {"status": "BLOCKED", "stage": "QAQC_GATE_BLOCKED", "reason": "QAQC_GATE_NOT_READY", "evidence": evidence, "version": VERSION}
    elif oid == "source_evidence":
        paths = _find(workspace, ("source_register", "evidence_register", "acquisition_register"), (".json",))
        evidence = _refs(paths, repository)
    elif oid == "project_zip":
        evidence = _refs([p for p in workspace.rglob("*.zip") if p.is_file() and p.stat().st_size > 0], repository)
        reason = "PROJECT_ZIP_ARTIFACT_REQUIRED"
    elif oid == "planning":
        evidence = _refs(_find(workspace, ("schedule", "planning_schedule", "project_schedule"), (".json", ".csv", ".xlsx", ".pdf")), repository)
        reason = "PROJECT_SCHEDULE_ARTIFACT_REQUIRED"
    elif oid == "structural_drawings":
        evidence = _refs(_find(workspace / "results" / "session_adapters" / "structural_engineering", ("drawing", "constructie", "structural"), (".dxf", ".svg", ".pdf", ".dwg")), repository)
    elif oid == "foundation_drawings":
        evidence = _refs(_find(workspace / "results" / "session_adapters" / "structural_engineering", ("foundation", "fundering"), (".dxf", ".svg", ".pdf", ".dwg")), repository)
    elif oid == "auto_video":
        evidence = _refs([p for p in workspace.rglob("*") if p.is_file() and p.suffix.casefold() in {".mp4", ".webm", ".mov"} and p.stat().st_size > 0], repository)
        reason = "AUTOMATIC_VIDEO_ARTIFACT_REQUIRED"
    elif oid == "foundation_design":
        evidence = _existing(repository, [x for x in structural if x.endswith("foundation_design_report.json")])
    else:
        combined = arch + dt + structural + permit + cost + reporting + closure
        evidence = _existing(repository, combined)

    if evidence:
        status = "PASSED"
        reason = None
        stage = "ARTIFACT_EVIDENCE_VERIFIED"
    return {
        "status": status,
        "stage": stage,
        "reason": reason,
        "evidence": evidence,
        "version": VERSION,
    }
