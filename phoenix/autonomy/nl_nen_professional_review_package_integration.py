from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import zipfile

from phoenix.autonomy.nl_nen_regulatory_review_bridge import (
    assess_nl_structural_basis,
    build_review_candidate_action_basis,
)

VERSION = "1.0.0"
PROJECT_ID = "MOSKEE-BUNSCHOTEN-E2E-REAL-001"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _country_code(
    repository: Path,
    session: dict[str, Any],
    project_context_path: Path | None,
) -> str | None:
    candidates: list[dict[str, Any]] = []
    if project_context_path and project_context_path.is_file():
        candidates.append(_read(project_context_path))
    bridge = session.get("bridge") if isinstance(session.get("bridge"), dict) else {}
    source_project_file = str(bridge.get("source_project_file") or "").strip()
    if source_project_file:
        source = repository / source_project_file
        if source.is_file():
            candidates.append(_read(source))
    selected = str(session.get("selected_project") or "").strip()
    if selected:
        for path in sorted((repository / "configs" / "projects").glob("*.json")):
            try:
                value = _read(path)
            except Exception:
                continue
            if str(value.get("project_id") or "").strip() == selected:
                candidates.append(value)
                break
    for value in candidates:
        facts = value.get("facts") if isinstance(value.get("facts"), dict) else {}
        raw = (
            facts.get("country_code")
            or value.get("country_code")
            or value.get("country")
            or value.get("jurisdiction")
        )
        normalized = str(raw or "").strip().upper()
        if normalized in {"NL", "NLD", "NEDERLAND", "NETHERLANDS", "THE NETHERLANDS"}:
            return "NL"
        if normalized:
            return normalized
    return None


def prepare_nl_professional_review_basis(
    *,
    repository: Path,
    session: dict[str, Any],
    workspace: Path,
    output_dir: Path,
    project_context_path: Path | None = None,
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    workspace = Path(workspace).resolve()
    output_dir = Path(output_dir).resolve()
    country_code = _country_code(repository, session, project_context_path)
    if country_code != "NL":
        return {"status": "NOT_APPLICABLE", "country_code": country_code, "paths": []}

    assessment = assess_nl_structural_basis(repository, mode="PROFESSIONAL_REVIEW_PACKAGE")
    candidate = build_review_candidate_action_basis()
    if assessment.status != "PASSED_FOR_REVIEW_PACKAGE":
        return {
            "status": "BLOCKED",
            "country_code": "NL",
            "blockers": list(assessment.blockers),
            "paths": [],
        }

    input_path = workspace / "inputs" / "structural" / "action_load_input_REQUIRED.json"
    assessment_path = output_dir / "nl_nen_regulatory_basis_assessment.json"
    basis_path = output_dir / "nl_nen_professional_review_action_basis.json"
    register_path = output_dir / "nl_nen_professional_review_integration_register.json"
    _write(input_path, candidate)
    _write(assessment_path, asdict(assessment))
    _write(basis_path, candidate)
    register = {
        "schema_version": "phoenix.nl-nen-professional-review-integration/1.0",
        "engine_version": VERSION,
        "project_id": str(session.get("selected_project") or session.get("brief") or ""),
        "country_code": "NL",
        "status": "PASSED_FOR_PROFESSIONAL_REVIEW_PACKAGE",
        "action_load_input": _repo_ref(input_path, repository),
        "regulatory_assessment": _repo_ref(assessment_path, repository),
        "candidate_basis": _repo_ref(basis_path, repository),
        "explicit_unresolved_items": list(candidate.get("explicit_unresolved_items") or []),
        "design_package_state": "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW",
        "formal_release": "LOCKED",
        "for_construction": False,
        "professional_review_required": True,
        "automatic_professional_approval": False,
    }
    _write(register_path, register)
    return {
        "status": register["status"],
        "country_code": "NL",
        "input": input_path,
        "assessment": assessment_path,
        "basis": basis_path,
        "register": register_path,
        "paths": [input_path, assessment_path, basis_path, register_path],
    }


_OUTPUT_PATTERNS: dict[str, tuple[str, ...]] = {
    "structural_calculation_report": ("calculation", "analysis_results", "verification", "structural_derivation_summary"),
    "structural_drawings": ("drawing",),
    "details_and_dimensions": ("detail", "dimension"),
    "load_and_combination_register": ("action_basis", "action_load", "combination"),
    "material_and_section_schedule": ("material", "section", "profile"),
    "technical_specification": ("specification", "bestek"),
    "qaqc_report": ("qaqc", "quality"),
    "assumptions_sources_deviations_register": ("assumption", "source_register", "deviation", "gap_register"),
    "digital_models": ("model", "digital_twin"),
    "solver_evidence": ("solver", "calculix", ".inp", ".frd", ".dat"),
}


def build_professional_review_package(
    *, repository: Path, workspace: Path, output_dir: Path, project_id: str
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    workspace = Path(workspace).resolve()
    output_dir = Path(output_dir).resolve()
    policy = _read(repository / "configs" / "phoenix" / "structural_review_release_policy_v1_0.json")
    required = list((policy.get("phase_a") or {}).get("required_outputs") or [])
    files = [p for p in workspace.rglob("*") if p.is_file()]
    coverage: dict[str, list[str]] = {}
    selected: set[Path] = set()
    for output_id in required:
        patterns = _OUTPUT_PATTERNS.get(output_id, (output_id,))
        matches = [
            path for path in files
            if any(pattern.casefold() in path.as_posix().casefold() for pattern in patterns)
        ]
        matches = sorted(set(matches))
        coverage[output_id] = [_repo_ref(path, repository) for path in matches]
        selected.update(matches)
    missing = [output_id for output_id in required if not coverage.get(output_id)]
    package_dir = output_dir / "professional_review_package"
    manifest_path = package_dir / "professional_review_package_manifest.json"
    zip_path = output_dir / f"{project_id}_PROFESSIONAL_REVIEW_PACKAGE.zip"
    manifest = {
        "schema_version": "phoenix.professional-review-package-manifest/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "status": (
            "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW"
            if not missing else "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW_INCOMPLETE"
        ),
        "required_outputs": required,
        "coverage": coverage,
        "missing_required_outputs": missing,
        "artifact_count": len(selected),
        "not_for_construction": True,
        "formal_release": "LOCKED",
        "professional_review_required": True,
        "automatic_professional_approval": False,
    }
    _write(manifest_path, manifest)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest_path, "professional_review_package_manifest.json")
        for path in sorted(selected):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            arcname = f"artifacts/{digest[:12]}_{path.name}"
            archive.write(path, arcname)
    return {
        "status": manifest["status"],
        "manifest": manifest_path,
        "zip": zip_path,
        "missing_required_outputs": missing,
        "artifact_count": len(selected),
        "paths": [manifest_path, zip_path],
    }
