"""PROJECT PHOENIX - SCIA Professional Engineering Bridge v1.0.

Target runtime:
- SCIA Engineer 18.1
- ESA_XML-first
- OpenAPI not required
- ADM reserved for later expansion

This bridge orchestrates SCIA execution and evidence capture. It does not declare
professional approval, code compliance, verification, production release or
FOR-CONSTRUCTION release.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

VERSION = "1.0.0"
ENGINE_ID = "PHX-SCIA-PROFESSIONAL-ENGINEERING-BRIDGE"
TARGET_SCIA = "SCIA Engineer 18.1"
DEFAULT_ESA_XML = r"C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe"

STATUS_READY = "READY_FOR_SCIA_EXECUTION"
STATUS_CALCULATED = "CALCULATED_UNVERIFIED"
STATUS_FAILED = "SCIA_EXECUTION_FAILED"
STATUS_INVALID = "INVALID_CALCULATION_PLAN"

ALLOWED_ANALYSIS_TYPES = {"LIN", "NEL"}
ALLOWED_DOCUMENT_TYPES = {"PDF", "RTF", "HTML", "TXT"}

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_verification_claim": False,
    "automatic_cross_verification_claim": False,
    "automatic_production_release": False,
    "automatic_for_construction_release": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("SCIA calculation plan must be a JSON object.")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_safe_path(repository: Path, value: str, *, must_exist: bool = False) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        if ".." in path.parts:
            raise ValueError(f"Unsafe repository-relative path: {value}")
        resolved = (repository / path).resolve()

    repo_resolved = repository.resolve()
    try:
        resolved.relative_to(repo_resolved)
    except ValueError:
        raise ValueError(f"Path outside repository is not allowed: {value}")

    if must_exist and not resolved.exists():
        raise FileNotFoundError(str(resolved))
    return resolved


def validate_plan(plan: dict[str, Any], repository: Path) -> list[str]:
    errors: list[str] = []
    required = ("schema_version", "project_id", "analysis_type", "seed_esa", "evidence_root")
    for key in required:
        if key not in plan or plan.get(key) in (None, ""):
            errors.append(f"missing:{key}")

    analysis = str(plan.get("analysis_type", "")).upper()
    if analysis and analysis not in ALLOWED_ANALYSIS_TYPES:
        errors.append(f"invalid:analysis_type:{analysis}")

    if plan.get("document_export"):
        export = plan["document_export"]
        if not isinstance(export, dict):
            errors.append("invalid:document_export")
        else:
            kind = str(export.get("type", "")).upper()
            if kind not in ALLOWED_DOCUMENT_TYPES:
                errors.append(f"invalid:document_export.type:{kind}")
            if not export.get("output_file"):
                errors.append("missing:document_export.output_file")

    try:
        if plan.get("seed_esa"):
            seed = _repo_safe_path(repository, str(plan["seed_esa"]), must_exist=True)
            if seed.suffix.lower() != ".esa":
                errors.append("invalid:seed_esa_extension")
        if plan.get("input_xml"):
            xml = _repo_safe_path(repository, str(plan["input_xml"]), must_exist=True)
            if xml.suffix.lower() != ".xml":
                errors.append("invalid:input_xml_extension")
        if plan.get("evidence_root"):
            _repo_safe_path(repository, str(plan["evidence_root"]), must_exist=False)
        if isinstance(plan.get("document_export"), dict) and plan["document_export"].get("output_file"):
            _repo_safe_path(repository, str(plan["document_export"]["output_file"]), must_exist=False)
        if plan.get("output_xml"):
            _repo_safe_path(repository, str(plan["output_xml"]), must_exist=False)
    except (ValueError, FileNotFoundError) as exc:
        errors.append(f"path:{exc}")
    return errors


def build_esa_xml_command(
    plan: dict[str, Any],
    repository: Path,
    esa_xml_executable: Path,
    working_esa: Path,
    log_path: Path,
) -> list[str]:
    analysis = str(plan["analysis_type"]).upper()
    args = [str(esa_xml_executable), analysis, str(working_esa)]

    if plan.get("input_xml"):
        args.append(str(_repo_safe_path(repository, str(plan["input_xml"]), must_exist=True)))

    export = plan.get("document_export")
    if isinstance(export, dict):
        kind = str(export["type"]).upper()
        output_file = _repo_safe_path(repository, str(export["output_file"]), must_exist=False)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        args.extend([f"/t{kind}", f"/o{output_file}"])
        if export.get("document_name"):
            args.append(f"/d{export['document_name']}")

    if plan.get("output_xml"):
        output_xml = _repo_safe_path(repository, str(plan["output_xml"]), must_exist=False)
        output_xml.parent.mkdir(parents=True, exist_ok=True)
        args.append(f"/x{output_xml}")
        if plan.get("output_xml_format"):
            args.append(f"/m{plan['output_xml_format']}")

    args.append(f"/l{log_path}")
    return args


def _collect_evidence_files(
    repository: Path,
    plan: dict[str, Any],
    evidence_root: Path,
    run_meta: dict[str, Any],
) -> dict[str, Any]:
    candidates: list[Path] = []
    seed = _repo_safe_path(repository, str(plan["seed_esa"]), must_exist=True)
    candidates.append(seed)

    if plan.get("input_xml"):
        candidates.append(_repo_safe_path(repository, str(plan["input_xml"]), must_exist=True))
    if plan.get("output_xml"):
        p = _repo_safe_path(repository, str(plan["output_xml"]), must_exist=False)
        if p.is_file():
            candidates.append(p)
    export = plan.get("document_export")
    if isinstance(export, dict):
        p = _repo_safe_path(repository, str(export["output_file"]), must_exist=False)
        if p.is_file():
            candidates.append(p)

    for value in plan.get("expected_project_generated_exports", []) or []:
        try:
            p = _repo_safe_path(repository, str(value), must_exist=False)
        except ValueError:
            continue
        if p.is_file():
            candidates.append(p)

    for name in ("scia_stdout.txt", "scia_stderr.txt", "scia_execution.log", "scia_command.json"):
        p = evidence_root / name
        if p.is_file():
            candidates.append(p)

    unique = []
    seen = set()
    for p in candidates:
        resolved = p.resolve()
        if resolved not in seen and p.is_file():
            seen.add(resolved)
            unique.append(p)

    files = []
    for p in unique:
        try:
            rel = p.resolve().relative_to(repository.resolve()).as_posix()
        except ValueError:
            rel = str(p.resolve())
        files.append({
            "path": rel,
            "sha256": sha256_file(p),
            "size_bytes": p.stat().st_size,
        })

    return {
        "schema_version": "phoenix.scia-evidence-manifest/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": plan["project_id"],
        "run_status": run_meta["status"],
        "analysis_type": str(plan["analysis_type"]).upper(),
        "scia_target": TARGET_SCIA,
        "files": files,
        "safety": dict(SAFETY),
    }


def execute_plan(
    plan: dict[str, Any],
    repository: Path,
    *,
    esa_xml_executable: Path | None = None,
    dry_run: bool = False,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    repository = repository.resolve()
    errors = validate_plan(plan, repository)
    if errors:
        return {
            "status": STATUS_INVALID,
            "errors": errors,
            "safety": dict(SAFETY),
        }

    esa_xml_executable = esa_xml_executable or Path(DEFAULT_ESA_XML)
    if not esa_xml_executable.is_file():
        return {
            "status": STATUS_INVALID,
            "errors": [f"ESA_XML executable not found: {esa_xml_executable}"],
            "safety": dict(SAFETY),
        }

    evidence_root = _repo_safe_path(repository, str(plan["evidence_root"]), must_exist=False)
    evidence_root.mkdir(parents=True, exist_ok=True)

    seed = _repo_safe_path(repository, str(plan["seed_esa"]), must_exist=True)
    working_esa = evidence_root / "scia_working_copy.esa"
    if not dry_run:
        shutil.copy2(seed, working_esa)
    else:
        working_esa = seed

    log_path = evidence_root / "scia_execution.log"
    command = build_esa_xml_command(plan, repository, esa_xml_executable, working_esa, log_path)
    _write_json(evidence_root / "scia_command.json", {"argv": command})

    base_result = {
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "project_id": plan["project_id"],
        "analysis_type": str(plan["analysis_type"]).upper(),
        "esa_xml_executable": str(esa_xml_executable),
        "seed_esa": str(seed),
        "working_esa": str(working_esa),
        "command_argv": command,
        "safety": dict(SAFETY),
    }

    if dry_run:
        return {
            **base_result,
            "status": STATUS_READY,
            "scia_calculation_started": False,
            "professional_review_required": True,
        }

    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(evidence_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        elapsed = time.time() - started
    except subprocess.TimeoutExpired as exc:
        (evidence_root / "scia_stdout.txt").write_text(exc.stdout or "", encoding="utf-8")
        (evidence_root / "scia_stderr.txt").write_text(exc.stderr or "", encoding="utf-8")
        return {
            **base_result,
            "status": STATUS_FAILED,
            "reason": "TIMEOUT",
            "timeout_seconds": timeout_seconds,
            "professional_review_required": True,
        }

    (evidence_root / "scia_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
    (evidence_root / "scia_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")

    expected = []
    if isinstance(plan.get("document_export"), dict):
        expected.append(_repo_safe_path(repository, str(plan["document_export"]["output_file"]), must_exist=False))
    if plan.get("output_xml"):
        expected.append(_repo_safe_path(repository, str(plan["output_xml"]), must_exist=False))
    for value in plan.get("expected_project_generated_exports", []) or []:
        expected.append(_repo_safe_path(repository, str(value), must_exist=False))

    missing_expected = [str(p) for p in expected if not p.is_file()]
    success = completed.returncode == 0 and not missing_expected

    result = {
        **base_result,
        "status": STATUS_CALCULATED if success else STATUS_FAILED,
        "scia_calculation_started": True,
        "return_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "missing_expected_outputs": missing_expected,
        "professional_review_required": True,
        "verification_status": "NOT_YET_INDEPENDENTLY_VERIFIED",
    }

    manifest = _collect_evidence_files(repository, plan, evidence_root, result)
    _write_json(evidence_root / "scia_evidence_manifest.json", manifest)
    _write_json(evidence_root / "scia_run_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--esa-xml", default=DEFAULT_ESA_XML)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()

    repository = Path(args.repository)
    plan = _read_json(Path(args.plan))
    result = execute_plan(
        plan,
        repository,
        esa_xml_executable=Path(args.esa_xml),
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["status"] in {STATUS_INVALID, STATUS_FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
