from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .package_b_licensed_source_traceability_r9_5_2_3 import (
    apply_package_b_traceability_to_r9_5_required_input_document,
)
from .project_stability_design_basis_decision_r9_5 import (
    build_project_stability_design_basis_decision,
)
from .project_stability_design_basis_input_evidence_qualification_r9_5_1 import (
    build_project_stability_design_basis_input_evidence_qualification,
)
from .stability_ab_project_policy_integration_r9_5_2_2 import (
    apply_ab_policy_to_r9_5_required_input_document,
    apply_ab_project_policy_to_r9_5_2_result,
)
from .stability_design_basis_decision_dossier_evidence_intake_r9_5_2 import (
    build_stability_design_basis_decision_dossier_evidence_intake,
)

ENGINE_ID = "PHX-RUNTIME-INPUT-MERGE-R9.5-REQUALIFICATION-R9.5.2.4"
VERSION = "R9.5.2.4"
INPUT_REL = Path("inputs") / "structural" / "global_stability_engineering_input_REQUIRED.json"
PACKAGE_B_SOURCE_ID = "NEN_EC2_STABILITY_PACKAGE_B_LICENSED_EXTRACT"

EXPECTED_B = {
    "GLOBAL_BUCKLING_FACTOR": ("minimum_critical_load_factor", 11.0),
    "SECOND_ORDER_AMPLIFICATION": ("max_amplification_factor", 1.10),
    "STOREY_STABILITY_INDEX": ("max_stability_index", 0.10),
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _json_bytes(value)
    tmp = path.with_name(path.name + ".r9_5_2_4.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

    readback = _read_json(path)
    if readback != dict(value):
        raise ValueError("R9.5.2.4 runtime input readback differs from the atomically written document")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != _sha256_bytes(data):
        raise ValueError("R9.5.2.4 runtime input SHA256 readback mismatch")
    return readback, digest


def normalize_r9_5_contract(document: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(document))
    root = _mapping(out.get("r9_5_project_stability_design_basis_decision"))
    if not root:
        return out

    checks = _mapping(root.get("checks"))
    for check_id, row_value in list(checks.items()):
        row = _mapping(row_value)
        # R9.5 requires an explicit applicability state, not a Python boolean.
        if row.get("applicability") is True:
            row["applicability"] = "APPLICABLE"
        elif row.get("applicability") is False:
            # Do not invent NOT_APPLICABLE from a false boolean.
            row["applicability"] = None
        checks[str(check_id)] = row
    root["checks"] = checks

    records = _mapping(root.get("source_records"))
    b = _mapping(records.get(PACKAGE_B_SOURCE_ID))
    if b:
        # R9.5's licensed-source contract uses LICENSED_STANDARD_SOURCE.
        if b.get("reference_type") == "LICENSED_STANDARD_EXTRACT":
            b["reference_type"] = "LICENSED_STANDARD_SOURCE"
        records[PACKAGE_B_SOURCE_ID] = b
    root["source_records"] = records

    root["r9_5_2_4_contract_normalization"] = {
        "engine": ENGINE_ID,
        "version": VERSION,
        "boolean_applicability_auto_promotion": False,
        "true_applicability_normalized_to": "APPLICABLE",
        "package_b_r9_5_reference_type": "LICENSED_STANDARD_SOURCE",
    }
    out["r9_5_project_stability_design_basis_decision"] = root
    return out


def _merge_ab_and_package_b(
    document: Mapping[str, Any],
    *,
    repository_root: Path,
    ab_policy_path: Path,
    package_b_registry_path: Path,
) -> dict[str, Any]:
    ab_policy = _read_json(Path(ab_policy_path))
    merged = apply_ab_policy_to_r9_5_required_input_document(document, ab_policy)
    merged = normalize_r9_5_contract(merged)
    merged = apply_package_b_traceability_to_r9_5_required_input_document(
        merged,
        repo_root=Path(repository_root),
        registry_path=Path(package_b_registry_path),
    )
    merged = normalize_r9_5_contract(merged)
    _validate_merged_package_b(merged)
    return merged


def _validate_merged_package_b(document: Mapping[str, Any]) -> None:
    root = _mapping(document.get("r9_5_project_stability_design_basis_decision"))
    if not root:
        raise ValueError("R9.5.2.4 merged R9.5 input section is missing")

    records = _mapping(root.get("source_records"))
    source = _mapping(records.get(PACKAGE_B_SOURCE_ID))
    if source.get("reference_type") != "LICENSED_STANDARD_SOURCE":
        raise ValueError("Package B source record is not normalized to LICENSED_STANDARD_SOURCE")
    if source.get("licensed_use_confirmed") is not True:
        raise ValueError("Package B licensed use is not confirmed in merged R9.5 input")
    if source.get("extraction_reviewed") is not True:
        raise ValueError("Package B extraction review is not confirmed in merged R9.5 input")
    if not str(source.get("source_file") or "").strip():
        raise ValueError("Package B source file is missing in merged R9.5 input")
    if len(str(source.get("sha256") or "")) != 64:
        raise ValueError("Package B source SHA256 is missing in merged R9.5 input")

    checks = _mapping(root.get("checks"))
    for check_id, (field, expected) in EXPECTED_B.items():
        row = _mapping(checks.get(check_id))
        if row.get("applicability") != "APPLICABLE":
            raise ValueError(f"{check_id} applicability is not APPLICABLE")
        if row.get("methodology_accepted") is not True:
            raise ValueError(f"{check_id} methodology is not accepted")
        criteria = _mapping(row.get("acceptance_criteria"))
        value = criteria.get(field)
        if value is None or float(value) != float(expected):
            raise ValueError(f"{check_id} criterion mismatch: {field}={value!r}")
        trace = _mapping(_mapping(row.get("criteria_traceability")).get(field))
        if trace.get("source_record_id") != PACKAGE_B_SOURCE_ID:
            raise ValueError(f"{check_id} traceability source record mismatch")
        if not str(trace.get("clause_reference") or "").strip():
            raise ValueError(f"{check_id} clause traceability is missing")


def _qualified_checks(r95: Mapping[str, Any]) -> list[str]:
    register = _mapping(r95.get("decision_register"))
    return sorted(
        check_id
        for check_id, row_value in register.items()
        if _mapping(row_value).get("state") == "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
    )


def _unresolved_checks(r95: Mapping[str, Any]) -> list[str]:
    register = _mapping(r95.get("decision_register"))
    return sorted(
        check_id
        for check_id, row_value in register.items()
        if _mapping(row_value).get("state") != "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
    )


def _package_resolution(
    r952: Mapping[str, Any],
    *,
    qualified_checks: list[str],
) -> tuple[list[str], list[str]]:
    qualified = set(qualified_checks)
    intake = _mapping(r952.get("evidence_intake"))
    packages = _mapping(intake.get("package_inputs"))
    resolved: list[str] = []
    unresolved: list[str] = []

    for package_id, package_value in packages.items():
        package = _mapping(package_value)
        checks = {str(x) for x in (package.get("checks") or [])}
        check_gate = bool(checks) and checks.issubset(qualified)

        if package_id == "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA":
            validation = _mapping(package.get("validation"))
            check_gate = (
                check_gate
                and validation.get("licensed_source_traceability_complete") is True
                and validation.get("licensed_use_confirmed") is True
                and validation.get("extraction_reviewed") is True
            )

        if check_gate:
            resolved.append(str(package_id))
        else:
            unresolved.append(str(package_id))

    return sorted(resolved), sorted(unresolved)


def _build_r95(
    *,
    project_id: str,
    merged_input: Mapping[str, Any],
    input_path: Path,
    r93_qualification: Mapping[str, Any],
    r94_initial: Mapping[str, Any],
    repository_root: Path,
    r95_policy_path: Path,
    suriname_rule_registry_path: Path,
    suriname_source_registry_path: Path,
    r94_policy_path: Path,
    r94_public_source_registry_path: Path,
) -> dict[str, Any]:
    try:
        candidate_name = input_path.relative_to(Path(repository_root)).as_posix()
    except ValueError:
        candidate_name = str(input_path)
    return build_project_stability_design_basis_decision(
        project_id=project_id,
        r93_qualification=r93_qualification,
        r94_initial=r94_initial,
        candidates=[(candidate_name, dict(merged_input))],
        policy_path=Path(r95_policy_path),
        suriname_rule_registry_path=Path(suriname_rule_registry_path),
        suriname_source_registry_path=Path(suriname_source_registry_path),
        r94_policy_path=Path(r94_policy_path),
        r94_public_source_registry_path=Path(r94_public_source_registry_path),
        repository_root=Path(repository_root),
    )


def build_runtime_input_merge_r9_5_requalification(
    *,
    project_id: str,
    workspace: Path,
    repository_root: Path,
    r93_qualification: Mapping[str, Any],
    r94_initial: Mapping[str, Any],
    r95_initial: Mapping[str, Any],
    r951_initial: Mapping[str, Any],
    r952_initial: Mapping[str, Any],
    r95_policy_path: Path,
    r951_policy_path: Path,
    r952_policy_path: Path,
    ab_policy_path: Path,
    package_b_registry_path: Path,
    suriname_rule_registry_path: Path,
    suriname_source_registry_path: Path,
    r94_policy_path: Path,
    r94_public_source_registry_path: Path,
) -> dict[str, Any]:
    workspace = Path(workspace)
    repository_root = Path(repository_root)
    input_path = workspace / INPUT_REL

    safety = {
        "one_pass_r9_5_requalification_only": True,
        "recursive_requalification": False,
        "technical_analysis_required_count": 0,
        "automatic_seismic_scope_decision": False,
        "automatic_weak_storey_professional_review": False,
        "automatic_alternate_path_independent_review": False,
        "automatic_code_compliance_claim": False,
        "automatic_structural_approval": False,
        "professional_structural_review_required": True,
        "production_release": "LOCKED",
    }

    try:
        r9523 = _mapping(r952_initial.get("r9_5_2_3"))
        if r9523.get("status") != "PACKAGE_B_LICENSED_SOURCE_TRACEABILITY_COMPLETE":
            raise ValueError("R9.5.2.3 Package B traceability is not complete")
        if not input_path.is_file():
            raise FileNotFoundError(input_path)

        original = _read_json(input_path)
        merged = _merge_ab_and_package_b(
            original,
            repository_root=repository_root,
            ab_policy_path=Path(ab_policy_path),
            package_b_registry_path=Path(package_b_registry_path),
        )
        readback, first_sha = _atomic_write_json(input_path, merged)

        r95 = _build_r95(
            project_id=project_id,
            merged_input=readback,
            input_path=input_path,
            r93_qualification=r93_qualification,
            r94_initial=r94_initial,
            repository_root=repository_root,
            r95_policy_path=Path(r95_policy_path),
            suriname_rule_registry_path=Path(suriname_rule_registry_path),
            suriname_source_registry_path=Path(suriname_source_registry_path),
            r94_policy_path=Path(r94_policy_path),
            r94_public_source_registry_path=Path(r94_public_source_registry_path),
        )

        qualified = _qualified_checks(r95)
        unresolved = _unresolved_checks(r95)

        if r95.get("status") == "PASSED":
            return {
                "schema_version": "phoenix.r9-5-2-4-runtime-input-merge-requalification/1.0",
                "engine": ENGINE_ID,
                "version": VERSION,
                "project_id": project_id,
                "status": "PASSED",
                "runtime_input_path": str(input_path),
                "runtime_input_sha256": first_sha,
                "r9_5_initial_status": r95_initial.get("status"),
                "r9_5_requalified": r95,
                "r9_5_1_requalified": None,
                "r9_5_2_requalified": None,
                "qualified_check_types": qualified,
                "unresolved_check_types": [],
                "resolved_package_ids": [],
                "unresolved_package_ids": [],
                "blockers": [],
                "summary": {
                    "required_check_type_count": len(_mapping(r95.get("decision_register"))),
                    "decision_qualified_check_count": len(qualified),
                    "unresolved_decision_check_count": 0,
                    "package_b_traceability_complete": True,
                    "technical_analysis_required_count": 0,
                    "one_pass_requalification_completed": True,
                },
                "safety": safety,
            }

        r951 = build_project_stability_design_basis_input_evidence_qualification(
            project_id=project_id,
            r95_result=r95,
            policy_path=Path(r951_policy_path),
        )

        next_input = (
            r951.get("prefilled_project_input")
            if isinstance(r951.get("prefilled_project_input"), Mapping)
            else readback
        )
        next_input = _merge_ab_and_package_b(
            next_input,
            repository_root=repository_root,
            ab_policy_path=Path(ab_policy_path),
            package_b_registry_path=Path(package_b_registry_path),
        )
        next_readback, second_sha = _atomic_write_json(input_path, next_input)

        r951 = deepcopy(dict(r951))
        r951["prefilled_project_input"] = next_readback
        r951["r9_5_2_4_runtime_merge"] = {
            "status": "PRESERVED_AFTER_R9_5_1_REGENERATION",
            "runtime_input_sha256": second_sha,
            "qualified_check_types_from_r9_5_requalification": qualified,
            "technical_analysis_required_count": 0,
        }

        existing_intake = (
            _mapping(r952_initial.get("evidence_intake"))
            if isinstance(r952_initial.get("evidence_intake"), Mapping)
            else {}
        )
        r952 = build_stability_design_basis_decision_dossier_evidence_intake(
            project_id=project_id,
            r951_result=r951,
            policy_path=Path(r952_policy_path),
            existing_intake=existing_intake,
        )
        r952 = apply_ab_project_policy_to_r9_5_2_result(
            r952_result=r952,
            policy_path=Path(ab_policy_path),
        )

        resolved_packages, unresolved_packages = _package_resolution(
            r952,
            qualified_checks=qualified,
        )

        blocker = {
            "reason": "R9_5_2_4_REQUALIFICATION_REMAINING_INPUT_REQUIRED",
            "message": (
                "R9.5.2.4 atomically merged the validated A+B / Package B evidence into the actual "
                "R9.5 runtime input and completed one R9.5 requalification pass. Package B licensed "
                "source traceability is complete. Remaining blockers are limited to still-unqualified "
                "decision/review packages; no new technical stability analysis is required."
            ),
            "decision_qualified_check_count": len(qualified),
            "unresolved_check_types": unresolved,
            "resolved_package_ids": resolved_packages,
            "unresolved_package_ids": unresolved_packages,
            "package_b_traceability_status": "COMPLETE",
            "technical_analysis_required_count": 0,
            "one_pass_requalification_completed": True,
        }

        return {
            "schema_version": "phoenix.r9-5-2-4-runtime-input-merge-requalification/1.0",
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "BLOCKED",
            "runtime_input_path": str(input_path),
            "runtime_input_sha256_after_initial_merge": first_sha,
            "runtime_input_sha256_after_r9_5_1_refresh": second_sha,
            "r9_5_initial_status": r95_initial.get("status"),
            "r9_5_requalified": r95,
            "r9_5_1_requalified": r951,
            "r9_5_2_requalified": r952,
            "qualified_check_types": qualified,
            "unresolved_check_types": unresolved,
            "resolved_package_ids": resolved_packages,
            "unresolved_package_ids": unresolved_packages,
            "blockers": [blocker],
            "summary": {
                "required_check_type_count": len(_mapping(r95.get("decision_register"))),
                "decision_qualified_check_count": len(qualified),
                "unresolved_decision_check_count": len(unresolved),
                "package_b_traceability_complete": True,
                "technical_analysis_required_count": 0,
                "one_pass_requalification_completed": True,
            },
            "safety": safety,
        }

    except Exception as exc:
        return {
            "schema_version": "phoenix.r9-5-2-4-runtime-input-merge-requalification/1.0",
            "engine": ENGINE_ID,
            "version": VERSION,
            "project_id": project_id,
            "status": "BLOCKED",
            "runtime_input_path": str(input_path),
            "r9_5_initial_status": r95_initial.get("status"),
            "r9_5_requalified": None,
            "r9_5_1_requalified": None,
            "r9_5_2_requalified": None,
            "qualified_check_types": [],
            "unresolved_check_types": [],
            "resolved_package_ids": [],
            "unresolved_package_ids": [],
            "blockers": [{
                "reason": "R9_5_2_4_RUNTIME_INPUT_MERGE_OR_REQUALIFICATION_FAILED",
                "message": (
                    "R9.5.2.4 failed closed while validating, atomically merging, or requalifying the "
                    "runtime stability input. No code-compliance or approval claim is made."
                ),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "technical_analysis_required_count": 0,
            }],
            "summary": {
                "required_check_type_count": 9,
                "decision_qualified_check_count": 0,
                "unresolved_decision_check_count": None,
                "package_b_traceability_complete": False,
                "technical_analysis_required_count": 0,
                "one_pass_requalification_completed": False,
            },
            "safety": safety,
        }
