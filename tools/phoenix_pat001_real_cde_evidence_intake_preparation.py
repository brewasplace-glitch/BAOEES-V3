"""Prepare the real C/D/E evidence intake for PHOENIX-PAT-001.

This utility is intentionally conservative:
- it inventories existing Phoenix evidence;
- it prepares the R9.5.2.9 combined intake file;
- it preserves any existing non-empty human/professional input;
- it never invents seismic applicability, numerical criteria, professional review,
  reviewer identity, independent evidence, acceptance, code compliance, or release approval.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

PACKAGE_C = "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
PACKAGE_D = "PKG-D-WEAK-STOREY-SCREENING-REVIEW"
PACKAGE_E = "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE"
PROJECT_ID = "PHOENIX-PAT-001"

COMBINED_FILENAME = "r9_5_remaining_evidence_combined_intake_REQUIRED.json"
GAP_FILENAME = "r9_5_remaining_evidence_CDE_GAP_REGISTER.json"
CONTEXT_FILENAME = "r9_5_remaining_evidence_CDE_EXISTING_EVIDENCE_CONTEXT.json"
CHECKLIST_FILENAME = "r9_5_remaining_evidence_CDE_PROFESSIONAL_REVIEW_CHECKLIST.md"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            value = json.loads(path.read_text(encoding=encoding))
            return value if isinstance(value, dict) else None
        except Exception:
            pass
    return None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def nonempty(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def merge_preserving_existing(default: Any, existing: Any) -> Any:
    if isinstance(default, dict):
        result = deepcopy(default)
        if isinstance(existing, dict):
            for key, value in existing.items():
                if key in result:
                    result[key] = merge_preserving_existing(result[key], value)
                else:
                    result[key] = deepcopy(value)
        return result
    if nonempty(existing):
        return deepcopy(existing)
    if isinstance(existing, bool):
        return existing
    return deepcopy(default)


def find_first(project_root: Path, filename: str) -> Path | None:
    matches = sorted(project_root.rglob(filename))
    return matches[0] if matches else None


def iter_dicts(value: Any, depth: int = 0) -> Iterable[dict[str, Any]]:
    if depth > 10:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child, depth + 1)


def extract_first(value: Any, key: str) -> Any:
    for item in iter_dicts(value):
        if key in item:
            return item[key]
    return None


def extract_unresolved_checks(value: Any) -> list[str]:
    for item in iter_dicts(value):
        checks = item.get("unresolved_check_types")
        if isinstance(checks, list):
            return [str(x) for x in checks]
    return []


def extract_unresolved_packages(value: Any) -> list[str]:
    for item in iter_dicts(value):
        packages = item.get("unresolved_package_ids")
        if isinstance(packages, list):
            return [str(x) for x in packages]
    return []


def contains_evidence_reference(value: Any, reference: str) -> bool:
    if isinstance(value, dict):
        return any(contains_evidence_reference(v, reference) for v in value.values())
    if isinstance(value, list):
        return any(contains_evidence_reference(v, reference) for v in value)
    return value == reference


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_c_gaps(value: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    invalid: list[str] = []
    status = value.get("seismic_applicability_status")
    if status not in {"APPLICABLE", "NOT_APPLICABLE"}:
        missing.append("seismic_applicability_status")
    for key in ("reference_type", "reference", "source_record_id", "scope_review_reference"):
        if not nonempty(value.get(key)):
            missing.append(key)
    if value.get("professional_scope_reviewed") is not True:
        missing.append("professional_scope_reviewed")

    if status == "APPLICABLE":
        criteria = value.get("criteria_if_applicable")
        if not isinstance(criteria, dict):
            missing.append("criteria_if_applicable")
        else:
            expected = {
                "SOFT_STOREY_STIFFNESS_RATIO": "minimum_ratio",
                "TORSIONAL_DRIFT_RATIO": "max_torsional_drift_ratio",
                "WEAK_STOREY_STRENGTH_RATIO": "minimum_ratio",
            }
            for check, numeric_key in expected.items():
                item = criteria.get(check)
                if not isinstance(item, dict):
                    missing.append(f"criteria_if_applicable.{check}")
                    continue
                if not nonempty(item.get(numeric_key)):
                    missing.append(f"criteria_if_applicable.{check}.{numeric_key}")
                if not nonempty(item.get("source_record_id")):
                    missing.append(f"criteria_if_applicable.{check}.source_record_id")
                if not nonempty(item.get("clause_reference")):
                    missing.append(f"criteria_if_applicable.{check}.clause_reference")
    return missing, invalid


def package_d_gaps(value: dict[str, Any]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    invalid: list[str] = []
    if not isinstance(value.get("screening_proxy_accepted_for_candidate_gate"), bool):
        missing.append("screening_proxy_accepted_for_candidate_gate")
    for key in ("screening_proxy_review_reference", "reviewer_scope", "review_status"):
        if not nonempty(value.get(key)) or str(value.get(key)).upper() == "INPUT_REQUIRED":
            missing.append(key)
    return missing, invalid


def package_e_gaps(value: dict[str, Any], repository: Path) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    invalid: list[str] = []
    for key in (
        "independent_engineering_evidence_reference",
        "repository_relative_source_file",
        "sha256",
        "independent_review_reference",
    ):
        if not nonempty(value.get(key)):
            missing.append(key)
    if not nonempty(value.get("independent_review_status")) or str(value.get("independent_review_status")).upper() == "INPUT_REQUIRED":
        missing.append("independent_review_status")
    if value.get("independently_verified_alternate_path") is not True:
        missing.append("independently_verified_alternate_path")

    trace = value.get("acceptance_criterion_and_traceability")
    if not isinstance(trace, dict):
        missing.append("acceptance_criterion_and_traceability")
    else:
        for key in ("minimum_residual_capacity_proxy_ratio", "source_record_id", "clause_reference"):
            if not nonempty(trace.get(key)):
                missing.append(f"acceptance_criterion_and_traceability.{key}")

    source = value.get("repository_relative_source_file")
    expected_sha = value.get("sha256")
    if nonempty(source):
        source_path = Path(str(source))
        if source_path.is_absolute() or ".." in source_path.parts:
            invalid.append("repository_relative_source_file:UNSAFE_PATH")
        else:
            full = repository / source_path
            if not full.is_file():
                invalid.append("repository_relative_source_file:FILE_NOT_FOUND")
            elif nonempty(expected_sha):
                actual = sha256_file(full)
                if actual.lower() != str(expected_sha).strip().lower():
                    invalid.append("sha256:MISMATCH")
    return missing, invalid


def build_checklist(context: dict[str, Any], gap: dict[str, Any], intake_path: Path) -> str:
    lines = [
        "# PHOENIX-PAT-001 — Real C/D/E Professional Evidence Review Checklist",
        "",
        f"Combined intake: `{intake_path.as_posix()}`",
        "",
        "## Current verified Phoenix state",
        "",
        f"- Technical analysis still required: `{context.get('technical_analysis_required_count')}`",
        f"- Current R9.5 status: `{context.get('r9_5_status')}`",
        f"- Unresolved checks: `{', '.join(context.get('unresolved_check_types') or [])}`",
        f"- Unresolved packages: `{', '.join(context.get('unresolved_package_ids') or [])}`",
        f"- Package B traceability complete: `{context.get('package_b_traceability_complete')}`",
        "",
        "## Package C — Seismic scope & criteria",
        "",
        "A professional reviewer must explicitly decide seismic applicability. Phoenix must not infer it.",
        "If APPLICABLE, each numerical criterion requires its own source record and clause/reference.",
        "",
        "Open fields:",
    ]
    for item in gap["packages"][PACKAGE_C]["missing_requirements"]:
        lines.append(f"- `{item}`")
    lines += [
        "",
        "## Package D — Weak-storey screening review",
        "",
        "The R8/R9.3 weak-storey result remains a candidate screening proxy until a professional review records an explicit decision.",
        "",
        "Open fields:",
    ]
    for item in gap["packages"][PACKAGE_D]["missing_requirements"]:
        lines.append(f"- `{item}`")
    lines += [
        "",
        "## Package E — Independent alternate-path evidence",
        "",
        "R9.3 alternate-path screening is not independent redistributed/nonlinear alternate-path proof.",
        "Independent engineering evidence, file integrity, review and acceptance-criterion traceability are required.",
        "",
        "Open fields:",
    ]
    for item in gap["packages"][PACKAGE_E]["missing_requirements"]:
        lines.append(f"- `{item}`")
    lines += [
        "",
        "## Release boundary",
        "",
        "- No automatic professional approval.",
        "- No automatic code-compliance claim.",
        "- No automatic seismic applicability decision.",
        "- No fabricated independent evidence.",
        "- Production release remains `LOCKED`.",
        "- FOR-CONSTRUCTION release remains `LOCKED`.",
        "",
        "After genuine professional evidence is entered, rerun the normal Phoenix project/structural session.",
        "R9.5.2.9 will normalize the intake, Packages E/C/D remain authoritative validators, and R9.5.2.8 may invoke controlled R9.5 requalification only when all three gates are truly eligible.",
        "",
    ]
    return "\n".join(lines)


def prepare(repository: Path, project_id: str) -> dict[str, Any]:
    repository = repository.resolve()
    project_root = repository / "projects" / "runtime" / project_id
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project runtime not found: {project_root}")

    template_path = repository / "templates" / "structural" / COMBINED_FILENAME
    template = read_json(template_path)
    if template is None:
        raise FileNotFoundError(f"R9.5.2.9 combined intake template not found: {template_path}")

    input_dir = project_root / "inputs" / "structural"
    input_dir.mkdir(parents=True, exist_ok=True)
    intake_path = input_dir / COMBINED_FILENAME

    existing = read_json(intake_path)
    combined = merge_preserving_existing(template, existing or {})
    combined["project_id"] = project_id
    combined["bundle_reference"] = "PHOENIX-PAT-001-REAL-CDE-EVIDENCE-INTAKE"
    combined["status"] = "INPUT_REQUIRED"

    r9524_path = find_first(project_root, "r9_5_2_4_runtime_input_merge_r9_5_requalification.json")
    r9524 = read_json(r9524_path) if r9524_path else None
    old_intake_path = find_first(project_root, "stability_design_basis_evidence_intake_REQUIRED.json")
    old_intake = read_json(old_intake_path) if old_intake_path else None
    r95_path = find_first(project_root, "r9_5_project_stability_design_basis_decision.json")
    r95 = read_json(r95_path) if r95_path else None
    r93_path = find_first(project_root, "r9_3_global_stability_technical_evidence.json")
    r93 = read_json(r93_path) if r93_path else None

    source_documents = [value for value in (r9524, old_intake, r95, r93) if isinstance(value, dict)]
    unresolved_checks: list[str] = []
    unresolved_packages: list[str] = []
    technical_required = None
    package_b_complete = None
    for document in source_documents:
        if not unresolved_checks:
            unresolved_checks = extract_unresolved_checks(document)
        if not unresolved_packages:
            unresolved_packages = extract_unresolved_packages(document)
        if technical_required is None:
            technical_required = extract_first(document, "technical_analysis_required_count")
        if package_b_complete is None:
            package_b_complete = extract_first(document, "package_b_traceability_complete")
            if package_b_complete is None:
                status = extract_first(document, "package_b_traceability_status")
                if isinstance(status, str):
                    package_b_complete = status.upper() == "COMPLETE"

    r95_status = r95.get("status") if isinstance(r95, dict) else None

    evidence_refs = {}
    for ref in (
        "R9.3:ALTERNATE_LOAD_PATH_EVIDENCE",
        "R9.3:SOFT_STOREY_STIFFNESS_RATIO",
        "R9.3:TORSIONAL_DRIFT_RATIO",
        "R9.3:WEAK_STOREY_STRENGTH_RATIO",
    ):
        evidence_refs[ref] = any(contains_evidence_reference(doc, ref) for doc in source_documents)

    context = {
        "schema_version": "phoenix.pat001-real-cde-existing-evidence-context/1.0",
        "project_id": project_id,
        "preparation_status": "EXISTING_EVIDENCE_INVENTORIED_PROFESSIONAL_INPUT_STILL_REQUIRED",
        "source_files": {
            "r9_5_2_4_requalification": str(r9524_path.relative_to(repository).as_posix()) if r9524_path else None,
            "legacy_r9_5_2_evidence_intake": str(old_intake_path.relative_to(repository).as_posix()) if old_intake_path else None,
            "r9_5_decision": str(r95_path.relative_to(repository).as_posix()) if r95_path else None,
            "r9_3_technical_evidence": str(r93_path.relative_to(repository).as_posix()) if r93_path else None,
        },
        "technical_analysis_required_count": technical_required,
        "r9_5_status": r95_status,
        "unresolved_check_types": unresolved_checks,
        "unresolved_package_ids": unresolved_packages,
        "package_b_traceability_complete": package_b_complete,
        "existing_r9_3_evidence_references": evidence_refs,
        "interpretation_boundaries": [
            "R8/R9.3 weak-storey strength is candidate screening only unless professionally accepted for the candidate gate.",
            "R9.3 alternate-path screening is not independent redistributed/nonlinear alternate-path proof.",
            "Seismic applicability and criteria require explicit traceable professional input.",
        ],
        "safety": {
            "automatic_professional_approval": False,
            "automatic_code_compliance_claim": False,
            "automatic_seismic_applicability_decision": False,
            "automatic_numerical_criteria_generation": False,
            "automatic_screening_proxy_acceptance": False,
            "automatic_independent_evidence_generation": False,
            "production_release": "LOCKED",
            "for_construction_release": "LOCKED",
        },
    }
    combined["evidence_context"] = deepcopy(context)

    packages = combined.get("package_inputs")
    if not isinstance(packages, dict):
        raise ValueError("Combined intake package_inputs is invalid.")

    c = packages.get(PACKAGE_C)
    d = packages.get(PACKAGE_D)
    e = packages.get(PACKAGE_E)
    if not all(isinstance(x, dict) for x in (c, d, e)):
        raise ValueError("Combined intake must contain Package C, D and E.")

    c_missing, c_invalid = package_c_gaps(c)
    d_missing, d_invalid = package_d_gaps(d)
    e_missing, e_invalid = package_e_gaps(e, repository)

    gap = {
        "schema_version": "phoenix.pat001-real-cde-gap-register/1.0",
        "project_id": project_id,
        "status": "PROFESSIONAL_EVIDENCE_REQUIRED",
        "technical_analysis_required_count": technical_required,
        "packages": {
            PACKAGE_C: {
                "status": "OPEN" if c_missing or c_invalid else "READY_FOR_EXISTING_PACKAGE_C_VALIDATOR",
                "missing_requirements": c_missing,
                "invalid_requirements": c_invalid,
            },
            PACKAGE_D: {
                "status": "OPEN" if d_missing or d_invalid else "READY_FOR_EXISTING_PACKAGE_D_VALIDATOR",
                "missing_requirements": d_missing,
                "invalid_requirements": d_invalid,
            },
            PACKAGE_E: {
                "status": "OPEN" if e_missing or e_invalid else "READY_FOR_EXISTING_PACKAGE_E_VALIDATOR",
                "missing_requirements": e_missing,
                "invalid_requirements": e_invalid,
            },
        },
        "all_intake_fields_ready_for_existing_validators": not any(
            x for x in (c_missing, c_invalid, d_missing, d_invalid, e_missing, e_invalid)
        ),
        "automatic_requalification_started": False,
        "next_authority": "Existing Package E/C/D validators, then R9.5.2.8 controlled evidence gate.",
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }

    context_path = input_dir / CONTEXT_FILENAME
    gap_path = input_dir / GAP_FILENAME
    checklist_path = input_dir / CHECKLIST_FILENAME

    write_json(intake_path, combined)
    write_json(context_path, context)
    write_json(gap_path, gap)
    checklist_path.write_text(build_checklist(context, gap, intake_path), encoding="utf-8")

    return {
        "status": "PREPARED",
        "project_id": project_id,
        "combined_intake": str(intake_path),
        "gap_register": str(gap_path),
        "evidence_context": str(context_path),
        "professional_review_checklist": str(checklist_path),
        "technical_analysis_required_count": technical_required,
        "unresolved_check_types": unresolved_checks,
        "unresolved_package_ids": unresolved_packages,
        "all_intake_fields_ready_for_existing_validators": gap["all_intake_fields_ready_for_existing_validators"],
        "production_release": "LOCKED",
        "for_construction_release": "LOCKED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=r"C:\PROJECT-PHOENIX")
    parser.add_argument("--project-id", default=PROJECT_ID)
    args = parser.parse_args()
    result = prepare(Path(args.repository), args.project_id)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
