"""PROJECT PHOENIX Professional Dossier & Controlled Review Engine v1.0.

General project-independent handoff layer:
- packages a technically verified structural calculation dossier;
- records exact SHA-256 evidence;
- creates an explicit reviewer-return template;
- validates a returned professional review record;
- compares reviewed replacement files against the submitted dossier;
- never turns review evidence into an automatic code-compliance or release claim.

This engine is intentionally downstream of:
1. SCIA Professional Engineering Bridge v1.0
2. Structural Independent Verification v1.0
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import shutil
import zipfile

VERSION = "1.0.0"
ENGINE_ID = "PHX-PROFESSIONAL-DOSSIER-CONTROLLED-REVIEW"

READY = "READY_FOR_PROFESSIONAL_REVIEW"
INPUT_REQUIRED = "DOSSIER_INPUT_REQUIRED"
RETURN_AWAITED = "AWAITING_CONFIRMED_PROFESSIONAL_REVIEW_RETURN"
RETURN_INVALID = "PROFESSIONAL_REVIEW_RETURN_INVALID"
RETURN_RECORDED = "PROFESSIONAL_REVIEW_RETURN_RECORDED"

ALLOWED_VERIFICATION_STATUSES = {
    "TECHNICALLY_VERIFIED",
    "TECHNICALLY_CROSS_VERIFIED",
}

ALLOWED_DECISIONS = {
    "REVIEWED_WITHOUT_CHANGES",
    "REVIEWED_WITH_CHANGES",
    "RECALCULATION_REQUIRED",
    "REJECTED",
}

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_production_release": False,
    "automatic_for_construction_release": False,
    "review_return_is_human_authored": True,
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _repo_rel(repository: Path, path: Path) -> str:
    return path.resolve().relative_to(repository.resolve()).as_posix()


def _sanitize_role(role: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in role.strip())
    if not cleaned:
        raise ValueError("Deliverable role cannot be empty.")
    return cleaned


def _load_sources(plan: dict[str, Any], repository: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    scia = None
    verification = None

    try:
        scia_path = _safe_path(repository, str(plan["scia_run_result"]), must_exist=True, file_only=True)
        scia = _read_json(scia_path)
    except Exception as exc:
        errors.append(f"scia_run_result:{exc}")

    try:
        verification_path = _safe_path(repository, str(plan["verification_result"]), must_exist=True, file_only=True)
        verification = _read_json(verification_path)
    except Exception as exc:
        errors.append(f"verification_result:{exc}")

    if scia is not None:
        if scia.get("status") != "CALCULATED_UNVERIFIED":
            errors.append("SCIA source must have status CALCULATED_UNVERIFIED")
        safety = scia.get("safety")
        if not isinstance(safety, dict):
            errors.append("SCIA safety object missing")
        else:
            if safety.get("production_release") != "LOCKED":
                errors.append("SCIA production release lock invalid")
            if safety.get("for_construction_release") != "LOCKED":
                errors.append("SCIA FOR-CONSTRUCTION release lock invalid")

    if verification is not None:
        if verification.get("status") not in ALLOWED_VERIFICATION_STATUSES:
            errors.append(
                "verification result must be TECHNICALLY_VERIFIED or TECHNICALLY_CROSS_VERIFIED"
            )
        safety = verification.get("safety")
        if not isinstance(safety, dict):
            errors.append("verification safety object missing")
        else:
            if safety.get("automatic_professional_approval") is not False:
                errors.append("verification automatic professional approval boundary invalid")
            if safety.get("production_release") != "LOCKED":
                errors.append("verification production release lock invalid")
            if safety.get("for_construction_release") != "LOCKED":
                errors.append("verification FOR-CONSTRUCTION release lock invalid")

    return scia, verification, errors


def reviewer_return_template(project_id: str, dossier_reference: str) -> dict[str, Any]:
    return {
        "schema_version": "phoenix.professional-review-return/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "dossier_reference": dossier_reference,
        "submission_confirmed": False,
        "review_record": {
            "reviewer_name": None,
            "reviewer_organization": None,
            "reviewer_role": None,
            "review_date": None,
            "signature_reference": None,
            "professional_scope": None,
        },
        "decision": "INPUT_REQUIRED",
        "review_comment": None,
        "reviewed_replacement_files": [],
        "declaration": (
            "This return is human/professional input. Phoenix records and validates it "
            "mechanically but does not author the professional decision."
        ),
    }


def _review_instructions(project_id: str, dossier_reference: str) -> str:
    return f"""# Professional Structural Review — {project_id}

Dossier reference: `{dossier_reference}`

## Reviewer actions

1. Review the submitted SCIA model and calculation/report evidence.
2. Review the Phoenix technical verification result and open review points.
3. Record reviewer name, organization, role, date, professional scope and signature reference.
4. Select exactly one decision:
   - `REVIEWED_WITHOUT_CHANGES`
   - `REVIEWED_WITH_CHANGES`
   - `RECALCULATION_REQUIRED`
   - `REJECTED`
5. If files were changed, return the reviewed replacement files and identify the submitted role they replace.
6. Set `submission_confirmed=true` only after the professional review is actually complete.

## Boundary

A validated review return records professional review evidence. It does not automatically:
- create a code-compliance claim;
- release Production;
- release FOR-CONSTRUCTION.

Production and FOR-CONSTRUCTION remain `LOCKED`.
"""


def _copy_deliverables(
    plan: dict[str, Any],
    repository: Path,
    submitted_root: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    items = plan.get("deliverables")
    if not isinstance(items, list) or not items:
        return [], ["deliverables list required"]

    manifest: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_roles: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            errors.append("deliverable entry must be object")
            continue
        role = str(item.get("role", "")).strip()
        path_value = item.get("path")
        required = item.get("required") is True
        if not role:
            errors.append("deliverable role required")
            continue
        if role in seen_roles:
            errors.append(f"duplicate deliverable role:{role}")
            continue
        seen_roles.add(role)

        if not path_value:
            if required:
                errors.append(f"required deliverable path missing:{role}")
            continue

        try:
            source = _safe_path(repository, str(path_value), must_exist=True, file_only=True)
        except Exception as exc:
            if required:
                errors.append(f"required deliverable unavailable:{role}:{exc}")
            continue

        role_safe = _sanitize_role(role)
        destination = submitted_root / f"{role_safe}__{source.name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        manifest.append({
            "role": role,
            "required": required,
            "source_path": _repo_rel(repository, source),
            "submitted_copy": destination.relative_to(submitted_root.parent).as_posix(),
            "sha256": sha256_file(destination),
            "size_bytes": destination.stat().st_size,
        })

    return manifest, errors


def create_dossier(plan: dict[str, Any], repository: Path) -> dict[str, Any]:
    repository = repository.resolve()
    if plan.get("schema_version") != "phoenix.professional-dossier-plan/1.0":
        return {"status": INPUT_REQUIRED, "errors": ["unsupported or missing schema_version"], "safety": dict(SAFETY)}

    project_id = str(plan.get("project_id", "")).strip()
    dossier_reference = str(plan.get("dossier_reference", "")).strip()
    dossier_root_value = plan.get("dossier_root")
    if not project_id or not dossier_reference or not dossier_root_value:
        return {
            "status": INPUT_REQUIRED,
            "errors": ["project_id, dossier_reference and dossier_root are required"],
            "safety": dict(SAFETY),
        }

    _, verification, source_errors = _load_sources(plan, repository)
    if source_errors:
        return {"status": INPUT_REQUIRED, "errors": source_errors, "safety": dict(SAFETY)}

    try:
        dossier_root = _safe_path(repository, str(dossier_root_value), must_exist=False)
    except Exception as exc:
        return {"status": INPUT_REQUIRED, "errors": [str(exc)], "safety": dict(SAFETY)}

    if dossier_root.exists() and any(dossier_root.iterdir()):
        return {
            "status": INPUT_REQUIRED,
            "errors": ["dossier_root must be new or empty for immutable submission packaging"],
            "safety": dict(SAFETY),
        }

    submitted_root = dossier_root / "submitted"
    submitted_root.mkdir(parents=True, exist_ok=True)

    deliverables, deliverable_errors = _copy_deliverables(plan, repository, submitted_root)
    if deliverable_errors:
        shutil.rmtree(dossier_root, ignore_errors=True)
        return {"status": INPUT_REQUIRED, "errors": deliverable_errors, "safety": dict(SAFETY)}

    required_roles = {
        str(x.get("role"))
        for x in plan.get("deliverables", [])
        if isinstance(x, dict) and x.get("required") is True
    }
    copied_roles = {x["role"] for x in deliverables}
    missing_required = sorted(required_roles - copied_roles)
    if missing_required:
        shutil.rmtree(dossier_root, ignore_errors=True)
        return {
            "status": INPUT_REQUIRED,
            "errors": [f"required deliverables not copied:{','.join(missing_required)}"],
            "safety": dict(SAFETY),
        }

    manifest = {
        "schema_version": "phoenix.professional-dossier-manifest/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": project_id,
        "dossier_reference": dossier_reference,
        "technical_verification_status": verification.get("status") if verification else None,
        "deliverables": deliverables,
        "immutable_submission": True,
        "review_return_required": True,
        "safety": dict(SAFETY),
    }
    _write_json(dossier_root / "DOSSIER_MANIFEST.json", manifest)

    return_path = dossier_root / "REVIEWER_RETURN_REQUIRED.json"
    _write_json(return_path, reviewer_return_template(project_id, dossier_reference))
    _write_text(dossier_root / "REVIEW_INSTRUCTIONS.md", _review_instructions(project_id, dossier_reference))

    # Create a deterministic-content review ZIP. ZIP metadata timestamps are not used as an engineering identity;
    # the dossier manifest hashes are authoritative.
    zip_path = dossier_root / "PROFESSIONAL_REVIEW_HANDOFF.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(dossier_root.rglob("*")):
            if not path.is_file() or path == zip_path:
                continue
            zf.write(path, arcname=path.relative_to(dossier_root).as_posix())

    result = {
        "schema_version": "phoenix.professional-dossier-result/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": project_id,
        "dossier_reference": dossier_reference,
        "status": READY,
        "dossier_root": _repo_rel(repository, dossier_root),
        "manifest": _repo_rel(repository, dossier_root / "DOSSIER_MANIFEST.json"),
        "reviewer_return": _repo_rel(repository, return_path),
        "handoff_zip": _repo_rel(repository, zip_path),
        "handoff_zip_sha256": sha256_file(zip_path),
        "technical_verification_status": verification.get("status") if verification else None,
        "professional_review_status": "NOT_YET_RETURNED",
        "safety": dict(SAFETY),
    }
    _write_json(dossier_root / "DOSSIER_RESULT.json", result)
    return result


def _validate_review_record(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["review_record required"]
    missing = []
    for key in (
        "reviewer_name",
        "reviewer_organization",
        "reviewer_role",
        "review_date",
        "signature_reference",
        "professional_scope",
    ):
        value = record.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(f"review_record.{key}")
    return missing


def process_review_return(
    repository: Path,
    dossier_root: Path,
    reviewer_return_path: Path,
) -> dict[str, Any]:
    repository = repository.resolve()
    dossier_root = dossier_root.resolve()
    try:
        dossier_root.relative_to(repository)
        reviewer_return_path.resolve().relative_to(repository)
    except ValueError:
        return {"status": RETURN_INVALID, "errors": ["review paths must remain inside repository"], "safety": dict(SAFETY)}

    manifest_path = dossier_root / "DOSSIER_MANIFEST.json"
    if not manifest_path.is_file():
        return {"status": RETURN_INVALID, "errors": ["DOSSIER_MANIFEST.json missing"], "safety": dict(SAFETY)}

    manifest = _read_json(manifest_path)
    review = _read_json(reviewer_return_path)

    if review.get("submission_confirmed") is not True:
        return {
            "status": RETURN_AWAITED,
            "professional_review_recorded": False,
            "safety": dict(SAFETY),
        }

    errors = _validate_review_record(review.get("review_record"))
    decision = str(review.get("decision", "")).upper()
    if decision not in ALLOWED_DECISIONS:
        errors.append("decision invalid or missing")

    if review.get("project_id") != manifest.get("project_id"):
        errors.append("project_id mismatch")
    if review.get("dossier_reference") != manifest.get("dossier_reference"):
        errors.append("dossier_reference mismatch")

    replacements = review.get("reviewed_replacement_files")
    if not isinstance(replacements, list):
        errors.append("reviewed_replacement_files must be a list")
        replacements = []

    if decision == "REVIEWED_WITH_CHANGES" and not replacements:
        errors.append("REVIEWED_WITH_CHANGES requires reviewed_replacement_files")

    submitted_roles = {x["role"]: x for x in manifest.get("deliverables", []) if isinstance(x, dict)}
    returned_files = []
    changed_roles = []

    returned_root = dossier_root / "returned"
    if not errors:
        returned_root.mkdir(parents=True, exist_ok=True)

        for item in replacements:
            if not isinstance(item, dict):
                errors.append("reviewed replacement entry must be object")
                continue
            role = str(item.get("replaces_role", "")).strip()
            source_value = item.get("path")
            if role not in submitted_roles:
                errors.append(f"replacement role not in submitted dossier:{role}")
                continue
            if not source_value:
                errors.append(f"replacement file missing for role:{role}")
                continue
            try:
                source = _safe_path(repository, str(source_value), must_exist=True, file_only=True)
            except Exception as exc:
                errors.append(f"replacement file invalid:{role}:{exc}")
                continue

            destination = returned_root / f"{_sanitize_role(role)}__{source.name}"
            shutil.copy2(source, destination)
            new_hash = sha256_file(destination)
            old_hash = submitted_roles[role]["sha256"]
            changed = new_hash != old_hash
            if changed:
                changed_roles.append(role)
            returned_files.append({
                "replaces_role": role,
                "source_path": _repo_rel(repository, source),
                "returned_copy": destination.relative_to(dossier_root).as_posix(),
                "submitted_sha256": old_hash,
                "returned_sha256": new_hash,
                "content_changed": changed,
                "size_bytes": destination.stat().st_size,
            })

    if errors:
        shutil.rmtree(returned_root, ignore_errors=True)
        return {"status": RETURN_INVALID, "errors": errors, "safety": dict(SAFETY)}

    if decision == "REVIEWED_WITH_CHANGES" and not changed_roles:
        shutil.rmtree(returned_root, ignore_errors=True)
        return {
            "status": RETURN_INVALID,
            "errors": ["REVIEWED_WITH_CHANGES requires at least one content-changed replacement file"],
            "safety": dict(SAFETY),
        }

    return_record = {
        "schema_version": "phoenix.controlled-professional-review-record/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": manifest["project_id"],
        "dossier_reference": manifest["dossier_reference"],
        "status": RETURN_RECORDED,
        "decision": decision,
        "review_record": deepcopy(review["review_record"]),
        "review_comment": review.get("review_comment"),
        "reviewer_return_sha256": sha256_file(reviewer_return_path),
        "returned_files": returned_files,
        "changed_roles": sorted(changed_roles),
        "professional_review_recorded": True,
        "requires_recalculation": decision in {"REVIEWED_WITH_CHANGES", "RECALCULATION_REQUIRED"},
        "review_rejected": decision == "REJECTED",
        "release_effect": "NONE_AUTOMATIC",
        "safety": dict(SAFETY),
    }
    _write_json(dossier_root / "CONTROLLED_REVIEW_RECORD.json", return_record)

    return return_record


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-dossier")
    create.add_argument("--repository", required=True)
    create.add_argument("--plan", required=True)

    process = sub.add_parser("process-return")
    process.add_argument("--repository", required=True)
    process.add_argument("--dossier-root", required=True)
    process.add_argument("--reviewer-return", required=True)

    args = parser.parse_args()
    repository = Path(args.repository).resolve()

    if args.command == "create-dossier":
        result = create_dossier(_read_json(Path(args.plan)), repository)
    else:
        dossier_root = _safe_path(repository, args.dossier_root, must_exist=True)
        reviewer_return = _safe_path(repository, args.reviewer_return, must_exist=True, file_only=True)
        result = process_review_return(repository, dossier_root, reviewer_return)

    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result.get("status") in {INPUT_REQUIRED, RETURN_INVALID, RETURN_AWAITED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
