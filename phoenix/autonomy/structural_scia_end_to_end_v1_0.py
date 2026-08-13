"""PROJECT PHOENIX Structural SCIA End-to-End Orchestrator v1.0.

Generic state-machine that drives an actual project through the already installed:
1. SCIA Professional Engineering Bridge v1.0
2. Structural Independent Verification v1.0
3. Professional Dossier & Controlled Review v1.0

PHOENIX-PAT-001 is the first project instance, but the engine itself is project-neutral.

Safety principles:
- a SCIA .ESA seed is real project input and is never fabricated;
- the baseline E2E solver smoke uses LIN only as a pipeline validation run;
- LIN E2E smoke is not a final project analysis-scope decision;
- verification tolerances are never invented;
- missing project verification criteria stop at INPUT_REQUIRED;
- missing professional dossier deliverables stop at DOSSIER_INPUT_REQUIRED;
- no professional review is simulated;
- Production and FOR-CONSTRUCTION remain LOCKED.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import argparse
import json
import os
import shutil

from phoenix.integrations.scia.professional_engineering_bridge_v1_0 import (
    execute_plan as execute_scia_plan,
    STATUS_CALCULATED,
)
from phoenix.autonomy.structural_independent_verification_v1_0 import (
    run_plan as run_verification_plan,
    STATUS_VERIFIED,
    STATUS_CROSS_VERIFIED,
)
from phoenix.autonomy.professional_dossier_controlled_review_v1_0 import (
    create_dossier,
    READY as DOSSIER_READY,
)

VERSION = "1.0.0"
ENGINE_ID = "PHX-STRUCTURAL-SCIA-END-TO-END"

DEFAULT_ESA_XML = r"C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe"

BLOCKED_SEED = "BLOCKED_SCIA_SEED_REQUIRED"
BLOCKED_SEED_SELECTION = "BLOCKED_SCIA_SEED_SELECTION_REQUIRED"
READY_SCIA = "READY_FOR_LIVE_SCIA_BASELINE"
SCIA_FAILED = "LIVE_SCIA_BASELINE_FAILED"
SCIA_CALCULATED_VERIFICATION_REQUIRED = "CALCULATED_UNVERIFIED_VERIFICATION_INPUT_REQUIRED"
VERIFICATION_FAILED = "TECHNICAL_VERIFICATION_FAILED"
VERIFIED_DOSSIER_REQUIRED = "TECHNICALLY_VERIFIED_DOSSIER_INPUT_REQUIRED"
CROSS_VERIFIED_DOSSIER_REQUIRED = "TECHNICALLY_CROSS_VERIFIED_DOSSIER_INPUT_REQUIRED"
READY_REVIEW = "READY_FOR_PROFESSIONAL_REVIEW"

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_project_analysis_scope_decision": False,
    "automatic_verification_tolerance_generation": False,
    "automatic_production_release": False,
    "automatic_for_construction_release": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _repo_rel(repository: Path, path: Path) -> str:
    return path.resolve().relative_to(repository.resolve()).as_posix()


def _safe_path(repository: Path, value: str, *, must_exist: bool = False, file_only: bool = False) -> Path:
    p = Path(value)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        if ".." in p.parts:
            raise ValueError(f"Unsafe repository-relative path: {value}")
        resolved = (repository / p).resolve()
    try:
        resolved.relative_to(repository.resolve())
    except ValueError:
        raise ValueError(f"Path outside repository: {value}")
    if must_exist:
        if file_only and not resolved.is_file():
            raise FileNotFoundError(str(resolved))
        if not file_only and not resolved.exists():
            raise FileNotFoundError(str(resolved))
    return resolved


def _candidate_score(path: Path, project_root: Path) -> int:
    rel = path.resolve().relative_to(project_root.resolve()).as_posix().lower()
    name = path.name.lower()
    score = 0
    if "/inputs/structural/scia/" in "/" + rel:
        score += 100
    elif "/inputs/structural/" in "/" + rel:
        score += 80
    elif "/inputs/" in "/" + rel:
        score += 50
    if "base" in name or "seed" in name or "model" in name:
        score += 20
    if "working" in name or "returned" in name or "reviewed" in name:
        score -= 40
    if "/results/" in "/" + rel or "/review/" in "/" + rel:
        score -= 30
    return score


def inventory_esa_candidates(repository: Path, project_id: str) -> list[dict[str, Any]]:
    project_root = repository / "projects" / "runtime" / project_id
    if not project_root.is_dir():
        return []
    candidates = []
    for path in project_root.rglob("*.esa"):
        if not path.is_file():
            continue
        candidates.append({
            "path": _repo_rel(repository, path),
            "score": _candidate_score(path, project_root),
            "size_bytes": path.stat().st_size,
        })
    return sorted(candidates, key=lambda x: (-x["score"], x["path"]))


def select_seed(candidates: list[dict[str, Any]]) -> tuple[str | None, str]:
    if not candidates:
        return None, BLOCKED_SEED
    top_score = candidates[0]["score"]
    top = [x for x in candidates if x["score"] == top_score]
    if len(top) != 1:
        return None, BLOCKED_SEED_SELECTION
    # Do not auto-select a low-confidence artifact from results/review locations.
    if top[0]["score"] < 50:
        return None, BLOCKED_SEED_SELECTION
    return str(top[0]["path"]), READY_SCIA


def _find_single(repository: Path, project_root: Path, patterns: list[str]) -> str | None:
    matches = []
    for pattern in patterns:
        matches.extend(path for path in project_root.rglob(pattern) if path.is_file())
    unique = []
    seen = set()
    for path in matches:
        r = path.resolve()
        if r not in seen:
            seen.add(r)
            unique.append(path)
    if len(unique) == 1:
        return _repo_rel(repository, unique[0])
    return None


def control_template(project_id: str, seed: str | None, verification_plan: str | None, dossier_plan: str | None) -> dict[str, Any]:
    return {
        "schema_version": "phoenix.structural-scia-e2e-control/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "execution_mode": "REAL_PROJECT_E2E",
        "scia": {
            "seed_esa": seed,
            "analysis_type": "LIN",
            "analysis_scope_note": (
                "LIN is used only for the first live E2E pipeline baseline. "
                "It is not an automatic final project analysis-scope decision."
            ),
            "input_xml": None,
            "document_export": None,
            "output_xml": None,
            "output_xml_format": None,
            "expected_project_generated_exports": [],
            "timeout_seconds": 3600,
        },
        "verification": {
            "plan_path": verification_plan,
            "required_for_technical_gate": True,
        },
        "professional_dossier": {
            "plan_path": dossier_plan,
            "required_for_review_gate": True,
        },
        "automatic_professional_review": False,
        "safety": dict(SAFETY),
    }


def _preserve_control(existing: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(generated)
    for top in ("scia", "verification", "professional_dossier"):
        old = existing.get(top)
        if not isinstance(old, dict):
            continue
        current = result.setdefault(top, {})
        for key, value in old.items():
            if value not in (None, "", [], {}):
                current[key] = deepcopy(value)
    # Never import unsafe release/professional claims from an edited control.
    result["automatic_professional_review"] = False
    result["safety"] = dict(SAFETY)
    return result


def _verification_request(project_id: str) -> dict[str, Any]:
    categories = {}
    for name in (
        "source_evidence",
        "global_equilibrium",
        "analytical_spot_checks",
        "load_path",
        "solver_health",
        "scia_calculix_cross_check",
        "mesh_convergence",
        "sensitivity",
        "evidence_integrity",
    ):
        categories[name] = {
            "applicability": "INPUT_REQUIRED",
            "note": "Set REQUIRED with genuine project evidence/criteria, or NOT_APPLICABLE with rationale + source_record_id.",
        }
    return {
        "schema_version": "phoenix.structural-independent-verification-plan/1.0",
        "project_id": project_id,
        "categories": categories,
        "safety_note": "No default engineering tolerances may be invented.",
    }


def _dossier_request(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": "phoenix.professional-dossier-plan/1.0",
        "project_id": project_id,
        "dossier_reference": f"{project_id}-STRUCTURAL-PROFESSIONAL-REVIEW-001",
        "scia_run_result": f"projects/runtime/{project_id}/results/scia/e2e_v1_0/run_001/scia_run_result.json",
        "verification_result": f"projects/runtime/{project_id}/results/verification/e2e_v1_0/structural_independent_verification_result.json",
        "dossier_root": f"projects/runtime/{project_id}/review/structural/e2e_v1_0/review_001",
        "deliverables": [
            {"role": "STRUCTURAL_BASIS_PDF", "path": None, "required": True},
            {"role": "STRUCTURAL_CALCULATION_PDF", "path": None, "required": True},
            {"role": "EDITABLE_REPORT_DOCX", "path": None, "required": True},
            {"role": "SCIA_ESA", "path": None, "required": True},
            {"role": "LOADS_AND_COMBINATIONS", "path": None, "required": True},
            {"role": "PHOENIX_QA_QC", "path": None, "required": True},
            {"role": "SCIA_CALCULIX_VERIFICATION", "path": None, "required": True},
            {"role": "ANALYTICAL_SPOT_CHECKS", "path": None, "required": True},
            {"role": "EVIDENCE_MANIFEST", "path": None, "required": True},
            {"role": "OPEN_REVIEW_POINTS", "path": None, "required": True},
        ],
        "safety_note": "Professional dossier packaging requires actual files; placeholders do not pass.",
    }


def prepare(repository: Path, project_id: str) -> dict[str, Any]:
    repository = repository.resolve()
    project_root = repository / "projects" / "runtime" / project_id
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project runtime root not found: {project_root}")

    input_root = project_root / "inputs" / "structural" / "scia_e2e_v1_0"
    input_root.mkdir(parents=True, exist_ok=True)

    candidates = inventory_esa_candidates(repository, project_id)
    selected_seed, seed_status = select_seed(candidates)

    verification_plan = _find_single(
        repository,
        project_root,
        [
            "*structural_independent_verification_plan*.json",
            "*verification_plan*.json",
        ],
    )
    dossier_plan = _find_single(
        repository,
        project_root,
        [
            "*professional_dossier_plan*.json",
            "*dossier_plan*.json",
        ],
    )

    control_path = input_root / "scia_e2e_control_REQUIRED.json"
    generated = control_template(project_id, selected_seed, verification_plan, dossier_plan)
    if control_path.is_file():
        try:
            generated = _preserve_control(_read_json(control_path), generated)
        except Exception:
            pass
    _write_json(control_path, generated)

    verification_request = input_root / "structural_independent_verification_plan_REQUIRED.json"
    if not verification_request.exists():
        _write_json(verification_request, _verification_request(project_id))

    dossier_request = input_root / "professional_dossier_plan_REQUIRED.json"
    if not dossier_request.exists():
        _write_json(dossier_request, _dossier_request(project_id))

    gaps = []
    if selected_seed is None:
        gaps.append({
            "gate": "SCIA_SEED",
            "status": seed_status,
            "requirement": "One unambiguous real project .ESA seed under the project runtime tree.",
            "automatic_fabrication_allowed": False,
        })

    if verification_plan is None:
        gaps.append({
            "gate": "TECHNICAL_VERIFICATION",
            "status": "VERIFICATION_PLAN_REQUIRED",
            "requirement": _repo_rel(repository, verification_request),
            "note": "Explicit project evidence and tolerances are required; Phoenix supplies no default engineering tolerances.",
        })

    if dossier_plan is None:
        gaps.append({
            "gate": "PROFESSIONAL_DOSSIER",
            "status": "DOSSIER_PLAN_REQUIRED",
            "requirement": _repo_rel(repository, dossier_request),
            "note": "Required PDF/DOCX/ESA/evidence deliverables must physically exist before packaging.",
        })

    inventory = {
        "schema_version": "phoenix.structural-scia-e2e-evidence-inventory/1.0",
        "project_id": project_id,
        "esa_candidates": candidates,
        "selected_seed": selected_seed,
        "verification_plan_discovered": verification_plan,
        "dossier_plan_discovered": dossier_plan,
        "safety": dict(SAFETY),
    }
    _write_json(input_root / "scia_e2e_evidence_inventory.json", inventory)

    readiness = {
        "schema_version": "phoenix.structural-scia-e2e-readiness/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": project_id,
        "status": seed_status,
        "scia_seed_ready": selected_seed is not None,
        "live_scia_baseline_ready": selected_seed is not None,
        "technical_verification_plan_discovered": verification_plan is not None,
        "professional_dossier_plan_discovered": dossier_plan is not None,
        "full_e2e_without_further_input_ready": (
            selected_seed is not None and verification_plan is not None and dossier_plan is not None
        ),
        "control_file": _repo_rel(repository, control_path),
        "gap_count": len(gaps),
        "safety": dict(SAFETY),
    }
    _write_json(input_root / "scia_e2e_readiness.json", readiness)
    _write_json(input_root / "scia_e2e_gap_register.json", {
        "schema_version": "phoenix.structural-scia-e2e-gap-register/1.0",
        "project_id": project_id,
        "gaps": gaps,
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    })

    return {
        "status": seed_status,
        "project_id": project_id,
        "workspace": _repo_rel(repository, input_root),
        "selected_seed": selected_seed,
        "esa_candidate_count": len(candidates),
        "verification_plan": verification_plan,
        "dossier_plan": dossier_plan,
        "gap_count": len(gaps),
        "live_scia_baseline_ready": selected_seed is not None,
        "full_e2e_without_further_input_ready": readiness["full_e2e_without_further_input_ready"],
        "safety": dict(SAFETY),
    }


def execute(repository: Path, project_id: str, esa_xml: Path = Path(DEFAULT_ESA_XML)) -> dict[str, Any]:
    repository = repository.resolve()
    project_root = repository / "projects" / "runtime" / project_id
    input_root = project_root / "inputs" / "structural" / "scia_e2e_v1_0"
    control_path = input_root / "scia_e2e_control_REQUIRED.json"
    if not control_path.is_file():
        prep = prepare(repository, project_id)
        if not prep["live_scia_baseline_ready"]:
            return prep

    control = _read_json(control_path)
    scia_cfg = control.get("scia")
    if not isinstance(scia_cfg, dict) or not scia_cfg.get("seed_esa"):
        return prepare(repository, project_id)

    seed = _safe_path(repository, str(scia_cfg["seed_esa"]), must_exist=True, file_only=True)

    results_root = project_root / "results" / "scia" / "e2e_v1_0" / "run_001"
    scia_plan = {
        "schema_version": "phoenix.scia-calculation-plan/1.0",
        "project_id": project_id,
        "analysis_type": str(scia_cfg.get("analysis_type", "LIN")).upper(),
        "seed_esa": _repo_rel(repository, seed),
        "input_xml": scia_cfg.get("input_xml"),
        "evidence_root": _repo_rel(repository, results_root),
        "document_export": scia_cfg.get("document_export"),
        "output_xml": scia_cfg.get("output_xml"),
        "output_xml_format": scia_cfg.get("output_xml_format"),
        "expected_project_generated_exports": scia_cfg.get("expected_project_generated_exports") or [],
    }
    _write_json(input_root / "scia_calculation_plan_E2E.json", scia_plan)

    scia_result = execute_scia_plan(
        scia_plan,
        repository,
        esa_xml_executable=esa_xml,
        dry_run=False,
        timeout_seconds=int(scia_cfg.get("timeout_seconds", 3600)),
    )
    if scia_result.get("status") != STATUS_CALCULATED:
        return {
            "status": SCIA_FAILED,
            "project_id": project_id,
            "scia_result": scia_result,
            "safety": dict(SAFETY),
        }

    verification_cfg = control.get("verification") if isinstance(control.get("verification"), dict) else {}
    verification_plan_value = verification_cfg.get("plan_path")
    if not verification_plan_value:
        return {
            "status": SCIA_CALCULATED_VERIFICATION_REQUIRED,
            "project_id": project_id,
            "scia_status": scia_result["status"],
            "verification_plan_required": _repo_rel(
                repository,
                input_root / "structural_independent_verification_plan_REQUIRED.json",
            ),
            "safety": dict(SAFETY),
        }

    verification_plan_path = _safe_path(
        repository,
        str(verification_plan_value),
        must_exist=True,
        file_only=True,
    )
    verification_output = project_root / "results" / "verification" / "e2e_v1_0"
    verification_result = run_verification_plan(
        verification_plan_path,
        repository,
        verification_output,
    )

    verification_status = verification_result.get("status")
    if verification_status not in {STATUS_VERIFIED, STATUS_CROSS_VERIFIED}:
        return {
            "status": VERIFICATION_FAILED,
            "project_id": project_id,
            "scia_status": scia_result["status"],
            "verification_result": verification_result,
            "safety": dict(SAFETY),
        }

    dossier_cfg = control.get("professional_dossier") if isinstance(control.get("professional_dossier"), dict) else {}
    dossier_plan_value = dossier_cfg.get("plan_path")
    if not dossier_plan_value:
        return {
            "status": (
                CROSS_VERIFIED_DOSSIER_REQUIRED
                if verification_status == STATUS_CROSS_VERIFIED
                else VERIFIED_DOSSIER_REQUIRED
            ),
            "project_id": project_id,
            "scia_status": scia_result["status"],
            "verification_status": verification_status,
            "professional_dossier_plan_required": _repo_rel(
                repository,
                input_root / "professional_dossier_plan_REQUIRED.json",
            ),
            "safety": dict(SAFETY),
        }

    dossier_plan_path = _safe_path(repository, str(dossier_plan_value), must_exist=True, file_only=True)
    dossier_result = create_dossier(_read_json(dossier_plan_path), repository)
    if dossier_result.get("status") != DOSSIER_READY:
        return {
            "status": "PROFESSIONAL_DOSSIER_INPUT_REQUIRED",
            "project_id": project_id,
            "scia_status": scia_result["status"],
            "verification_status": verification_status,
            "dossier_result": dossier_result,
            "safety": dict(SAFETY),
        }

    return {
        "status": READY_REVIEW,
        "project_id": project_id,
        "scia_status": scia_result["status"],
        "verification_status": verification_status,
        "dossier_status": dossier_result["status"],
        "handoff_zip": dossier_result.get("handoff_zip"),
        "professional_review_status": "NOT_YET_RETURNED",
        "safety": dict(SAFETY),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "execute"))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--esa-xml", default=DEFAULT_ESA_XML)
    args = parser.parse_args()

    repository = Path(args.repository)
    if args.action == "prepare":
        result = prepare(repository, args.project_id)
    else:
        result = execute(repository, args.project_id, Path(args.esa_xml))

    print(json.dumps(result, indent=2, ensure_ascii=True))

    # Project input gates are valid workflow states, not software crashes.
    software_failure_statuses = {SCIA_FAILED, VERIFICATION_FAILED}
    if result.get("status") in software_failure_statuses:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
