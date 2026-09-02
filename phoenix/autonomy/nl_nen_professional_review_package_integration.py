from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import zipfile

from phoenix.autonomy.nl_nen_regulatory_review_bridge import (
    assess_nl_structural_basis,
    build_review_candidate_action_basis,
)

VERSION = "1.1.0"
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


_EXPLICIT_FIELD_PATTERN = re.compile(
    r"(?i)(material|strength|grade|class|section|profile|cross_section|elastic|young|"
    r"poisson|density|yield|compressive|thickness|width|height|diameter)"
)
_PLACEHOLDER_TOKENS = {
    "", "NONE", "NULL", "UNKNOWN", "UNRESOLVED", "MISSING", "REQUIRED", "TBD",
    "GENERIC", "CONCEPT", "NOT_SET", "NOT_AVAILABLE", "AUTO",
}
_ELEMENT_ID_KEYS = ("element_id", "member_id", "id", "elementId", "memberId")


def _optional_read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read(path)
    except Exception:
        return {}


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _is_explicit_scalar(value: Any) -> bool:
    if not isinstance(value, (str, int, float, bool)) or isinstance(value, bool):
        return False
    if isinstance(value, str):
        normalized = re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")
        if normalized in _PLACEHOLDER_TOKENS:
            return False
        if any(token in normalized for token in ("UNKNOWN", "UNRESOLVED", "MISSING", "REQUIRED", "TBD", "GENERIC")):
            return False
    return True


def _collect_missing_element_ids(*values: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for value in values:
        for record in _iter_dicts(value):
            ids = record.get("missing_element_ids")
            if isinstance(ids, list):
                found.extend(str(item).strip() for item in ids if str(item).strip())
    return list(dict.fromkeys(found))


def _collect_blockers(source_ref: str, value: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for record in _iter_dicts(value):
        blockers = record.get("blockers")
        if not isinstance(blockers, list):
            continue
        for blocker in blockers:
            if isinstance(blocker, dict):
                item = dict(blocker)
            else:
                item = {"reason": str(blocker)}
            item["source"] = source_ref
            if item not in found:
                found.append(item)
    return found


def _record_id(record: dict[str, Any]) -> str | None:
    for key in _ELEMENT_ID_KEYS:
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return None


def _explicit_fields(record: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in record.items():
        if not _EXPLICIT_FIELD_PATTERN.search(str(key)):
            continue
        if _is_explicit_scalar(value):
            found[str(key)] = value
        elif isinstance(value, dict):
            for child_key, child_value in value.items():
                if _is_explicit_scalar(child_value):
                    found[f"{key}.{child_key}"] = child_value
    return found


def _source_derived_element_values(
    missing_ids: list[str], source_models: list[tuple[str, dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    wanted = set(missing_ids)
    result: dict[str, dict[str, Any]] = {element_id: {} for element_id in missing_ids}
    for source_ref, model in source_models:
        for record in _iter_dicts(model):
            element_id = _record_id(record)
            if element_id not in wanted:
                continue
            values = _explicit_fields(record)
            if values:
                result[element_id][source_ref] = values
    return result


def build_structural_review_input_pack(
    *, repository: Path, workspace: Path, output_dir: Path, project_id: str
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    workspace = Path(workspace).resolve()
    output_dir = Path(output_dir).resolve()
    analysis_path = workspace / "inputs/structural/structural_analysis_basis_REQUIRED.json"
    action_path = workspace / "inputs/structural/action_load_input_REQUIRED.json"
    solver_path = output_dir / "validated_v8_1_to_v8_12/v8_3/autonomous_solver_basis_register.json"
    model_path = output_dir / "v8_0_structural_derivation/model/structural_candidate_model.json"
    model_v8_path = output_dir / "v8_0_structural_derivation/digital_twin/structural_candidate_model_v8_0_0.json"
    gap_paths = [
        output_dir / "structural_design_material_basis_gap_register.json",
        workspace / "results/session_adapters/architecture/structural_design_material_basis_gap_register.json",
    ]
    sources = {
        _repo_ref(path, repository): _optional_read(path)
        for path in [analysis_path, action_path, solver_path, model_path, model_v8_path, *gap_paths]
        if path.is_file()
    }
    analysis = _optional_read(analysis_path)
    action = _optional_read(action_path)
    solver = _optional_read(solver_path)
    gaps = [_optional_read(path) for path in gap_paths if path.is_file()]
    missing_ids = _collect_missing_element_ids(analysis, solver, *gaps)
    source_models = [
        (_repo_ref(path, repository), _optional_read(path))
        for path in (model_path, model_v8_path)
        if path.is_file()
    ]
    derived_by_element = _source_derived_element_values(missing_ids, source_models)
    required_fields = [
        "material_designation_and_strength_class",
        "section_or_profile_geometry",
        "solver_material_properties",
        "source_reference",
        "professional_confirmation",
    ]
    schedule = []
    for element_id in missing_ids:
        derived = derived_by_element.get(element_id) or {}
        schedule.append(
            {
                "element_id": element_id,
                "source_derived_values": derived,
                "required_fields": required_fields,
                "status": "SOURCE_VALUES_PARTIAL_REVIEW_INPUT_REQUIRED" if derived else "REVIEW_INPUT_REQUIRED",
            }
        )
    blockers: list[dict[str, Any]] = []
    for source_ref, value in sources.items():
        blockers.extend(_collect_blockers(source_ref, value))
    explicit_unresolved = list(action.get("explicit_unresolved_items") or [])
    material_gaps: list[dict[str, Any]] = []
    for gap_value in gaps:
        for item in gap_value.get("gaps") or []:
            if isinstance(item, dict) and item not in material_gaps:
                material_gaps.append(item)
    unresolved = bool(missing_ids or blockers or explicit_unresolved or material_gaps)
    pack_dir = output_dir / "review_input_pack"
    pack_path = pack_dir / "source_derived_structural_review_input_pack.json"
    spec_path = output_dir / "specification/structural_technical_specification_review_draft.md"
    qaqc_path = output_dir / "qaqc/structural_qaqc_blocker_report.json"
    qaqc_md_path = output_dir / "qaqc/structural_qaqc_blocker_report.md"
    pack = {
        "schema_version": "phoenix.source-derived-structural-review-input-pack/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "status": "REVIEW_INPUT_REQUIRED" if unresolved else "SOURCE_DERIVED_REVIEW_INPUT_READY_FOR_PROFESSIONAL_CONFIRMATION",
        "strategy": "SOURCE_DERIVATION_WITHOUT_INVENTED_ENGINEERING_VALUES",
        "source_documents": sorted(sources),
        "source_derived_action_basis": {
            "basis": action.get("basis"),
            "release_class": action.get("release_class"),
            "actions": list(action.get("actions") or []),
            "combinations": list(action.get("combinations") or []),
        },
        "explicit_unresolved_norm_and_project_items": explicit_unresolved,
        "v8_3_blockers": blockers,
        "material_design_basis_gaps": material_gaps,
        "element_input_schedule": schedule,
        "missing_element_count": len(missing_ids),
        "source_derived_element_count": sum(bool(row["source_derived_values"]) for row in schedule),
        "invented_values": [],
        "solver_execution_allowed": False,
        "structural_release": "LOCKED",
        "for_construction": False,
        "professional_review_required": True,
        "next_gate": "CONFIRMED_SOURCE_BACKED_MATERIAL_SECTION_AND_NORM_INPUT",
    }
    _write(pack_path, pack)
    spec_lines = [
        "# Structural Technical Specification â€” Source-Derived Review Draft",
        "",
        f"Project: `{project_id}`",
        "",
        "Status: **REVIEW INPUT REQUIRED / NOT FOR CONSTRUCTION**",
        "",
        "This controlled draft records only values present in traceable project or norm sources. "
        "No missing material class, strength, section, solver property or release decision is inferred.",
        "",
        "## Source-derived action basis",
        "",
        f"- Basis: `{action.get('basis') or 'UNRESOLVED'}`",
        f"- Release class: `{action.get('release_class') or 'UNRESOLVED'}`",
        f"- Actions recorded: `{len(action.get('actions') or [])}`",
        f"- Combinations recorded: `{len(action.get('combinations') or [])}`",
        "",
        "## Element input schedule",
        "",
        "| Element | Source-derived values | Status |",
        "|---|---|---|",
    ]
    for row in schedule:
        rendered = json.dumps(row["source_derived_values"], ensure_ascii=False, sort_keys=True)
        spec_lines.append(f"| {row['element_id']} | {rendered} | {row['status']} |")
    if not schedule:
        spec_lines.append("| â€” | No missing element identifiers reported | PROFESSIONAL_CONFIRMATION_REQUIRED |")
    spec_lines.extend(["", "## Explicit unresolved items", ""])
    unresolved_rows = explicit_unresolved or ["No explicit norm item list was found; professional confirmation remains required."]
    spec_lines.extend(f"- {item}" for item in unresolved_rows)
    spec_lines.extend([
        "",
        "## Release controls",
        "",
        "- Solver execution: BLOCKED pending confirmed source-backed input",
        "- Structural release: LOCKED",
        "- For construction: NO",
        "- Automatic professional approval: NO",
        "",
    ])
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("\n".join(spec_lines), encoding="utf-8")
    qaqc = {
        "schema_version": "phoenix.structural-review-input-qaqc/1.0",
        "project_id": project_id,
        "status": "BLOCKED_PENDING_SOURCE_BACKED_DESIGN_INPUT" if unresolved else "READY_FOR_PROFESSIONAL_CONFIRMATION",
        "checks": {
            "invented_engineering_values_absent": not bool(pack["invented_values"]),
            "source_documents_registered": bool(pack["source_documents"]),
            "element_schedule_generated": bool(schedule),
            "solver_deck_release_allowed": False,
            "formal_release_allowed": False,
        },
        "missing_element_count": len(missing_ids),
        "unresolved_norm_and_project_items": explicit_unresolved,
        "blocker_count": len(blockers),
        "material_gap_count": len(material_gaps),
        "input_pack": _repo_ref(pack_path, repository),
        "technical_specification_draft": _repo_ref(spec_path, repository),
        "production_release": "LOCKED",
        "for_construction": False,
        "professional_review_required": True,
    }
    _write(qaqc_path, qaqc)
    qaqc_md_path.parent.mkdir(parents=True, exist_ok=True)
    qaqc_md_path.write_text(
        "# Structural QA/QC Blocker Report\n\n"
        f"Status: **{qaqc['status']}**\n\n"
        f"Missing element inputs: {len(missing_ids)}  \n"
        f"Recorded blockers: {len(blockers)}  \n"
        f"Material/design-basis gaps: {len(material_gaps)}  \n\n"
        "Solver execution and release remain locked. No missing engineering value was invented.\n",
        encoding="utf-8",
    )
    return {
        "status": pack["status"],
        "pack": pack_path,
        "technical_specification": spec_path,
        "qaqc": qaqc_path,
        "qaqc_markdown": qaqc_md_path,
        "missing_element_count": len(missing_ids),
        "solver_execution_allowed": False,
        "paths": [pack_path, spec_path, qaqc_path, qaqc_md_path],
    }


_OUTPUT_PATTERNS: dict[str, tuple[str, ...]] = {
    "structural_calculation_report": ("calculation_report", "structural_report"),
    "structural_drawings": ("structural_drawing", "foundation_drawing"),
    "details_and_dimensions": ("detail", "dimension"),
    "load_and_combination_register": ("action_basis", "action_load", "combination"),
    "material_and_section_schedule": ("material", "section", "profile"),
    "technical_specification": ("technical_specification", "bestek"),
    "qaqc_report": ("qaqc", "quality"),
    "assumptions_sources_deviations_register": ("assumption", "source_register", "deviation", "gap_register"),
    "digital_models": ("model", "digital_twin"),
    "solver_evidence": (".inp",),
}


def _qualifies(output_id: str, path: Path) -> bool:
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    if output_id == "solver_evidence":
        return suffix == ".inp"
    if output_id == "structural_drawings":
        return suffix in {".svg", ".pdf", ".dxf", ".dwg", ".ifc"} and (
            "structural" in name or "foundation" in name
        )
    if output_id == "structural_calculation_report":
        return suffix in {".json", ".md", ".pdf", ".docx"} and (
            "calculation_report" in name or "structural_report" in name
        )
    if output_id == "technical_specification":
        return suffix in {".md", ".pdf", ".docx", ".json"} and (
            "technical_specification" in name or "bestek" in name
        )
    if output_id == "qaqc_report":
        return suffix in {".json", ".md", ".pdf", ".docx"} and (
            "qaqc" in name or "quality" in name
        )
    return True


def build_professional_review_package(
    *, repository: Path, workspace: Path, output_dir: Path, project_id: str
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    workspace = Path(workspace).resolve()
    output_dir = Path(output_dir).resolve()
    policy = _read(repository / "configs/phoenix/structural_review_release_policy_v1_0.json")
    required = list((policy.get("phase_a") or {}).get("required_outputs") or [])
    package_dir = output_dir / "professional_review_package"
    manifest_path = package_dir / "professional_review_package_manifest.json"
    zip_path = output_dir / f"{project_id}_PROFESSIONAL_REVIEW_PACKAGE.zip"
    files = [
        path for path in workspace.rglob("*")
        if path.is_file()
        and package_dir not in path.parents
        and path.resolve() != zip_path.resolve()
        and path.suffix.casefold() != ".zip"
    ]
    coverage: dict[str, list[str]] = {}
    selected: set[Path] = set()
    for output_id in required:
        patterns = _OUTPUT_PATTERNS.get(output_id, (output_id,))
        matches = [
            path for path in files
            if any(pattern.casefold() in path.as_posix().casefold() for pattern in patterns)
            and _qualifies(output_id, path)
        ]
        matches = sorted(set(matches))
        coverage[output_id] = [_repo_ref(path, repository) for path in matches]
        selected.update(matches)
    pack_path = output_dir / "review_input_pack/source_derived_structural_review_input_pack.json"
    pack = _optional_read(pack_path)
    if pack_path.is_file():
        selected.add(pack_path)
    blocking_review_inputs: list[dict[str, Any]] = []
    if pack and pack.get("status") == "REVIEW_INPUT_REQUIRED":
        blocking_review_inputs.append(
            {
                "id": "SOURCE_BACKED_V8_3_INPUT_REQUIRED",
                "input_pack": _repo_ref(pack_path, repository),
                "missing_element_count": int(pack.get("missing_element_count") or 0),
                "next_gate": pack.get("next_gate"),
            }
        )
    missing = [output_id for output_id in required if not coverage.get(output_id)]
    status = (
        "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW"
        if not missing and not blocking_review_inputs
        else "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW_INCOMPLETE"
    )
    archive_rows: list[dict[str, str]] = []
    deduplicated: list[dict[str, str]] = []
    canonical_by_content_and_name: dict[tuple[str, str], Path] = {}
    for path in sorted(selected):
        content_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        key = (content_sha, path.name.casefold())
        if key in canonical_by_content_and_name:
            deduplicated.append(
                {
                    "source": _repo_ref(path, repository),
                    "canonical_source": _repo_ref(canonical_by_content_and_name[key], repository),
                    "sha256": content_sha,
                }
            )
            continue
        canonical_by_content_and_name[key] = path
        archive_rows.append(
            {
                "source": _repo_ref(path, repository),
                "sha256": content_sha,
                "arcname": f"artifacts/{content_sha[:16]}_{path.name}",
            }
        )
    arcnames = [row["arcname"] for row in archive_rows]
    if len(arcnames) != len(set(arcnames)):
        raise RuntimeError("Professional review archive member collision remains after deduplication.")
    manifest = {
        "schema_version": "phoenix.professional-review-package-manifest/1.1",
        "engine_version": VERSION,
        "project_id": project_id,
        "status": status,
        "required_outputs": required,
        "coverage": coverage,
        "missing_required_outputs": missing,
        "blocking_review_inputs": blocking_review_inputs,
        "review_input_pack": _repo_ref(pack_path, repository) if pack_path.is_file() else None,
        "selected_source_count": len(selected),
        "archive_artifact_count": len(archive_rows),
        "deduplicated_source_count": len(deduplicated),
        "deduplicated_sources": deduplicated,
        "archive_entries": archive_rows,
        "not_for_construction": True,
        "formal_release": "LOCKED",
        "professional_review_required": True,
        "automatic_professional_approval": False,
    }
    _write(manifest_path, manifest)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(manifest_path, "professional_review_package_manifest.json")
        for row in archive_rows:
            archive.write(repository / row["source"], row["arcname"])
    return {
        "status": manifest["status"],
        "manifest": manifest_path,
        "zip": zip_path,
        "missing_required_outputs": missing,
        "blocking_review_inputs": blocking_review_inputs,
        "artifact_count": len(archive_rows),
        "deduplicated_source_count": len(deduplicated),
        "paths": [manifest_path, zip_path],
    }
