from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

REPOSITORY_BOOTSTRAP = Path(__file__).resolve().parents[1]
if str(REPOSITORY_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_BOOTSTRAP))

from phoenix.autonomy.nl_nen_professional_review_package_integration import (
    build_professional_review_package,
)
from phoenix.local_app.architectural_orchestration_runtime import (
    ArchitecturalOrchestrationRuntime,
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _job_value(job: object, name: str, default=None):
    return getattr(job, name, default)


def _job_dict(job: object) -> dict:
    if hasattr(job, "to_dict"):
        return job.to_dict()
    return {
        name: _job_value(job, name)
        for name in (
            "job_id",
            "project_file",
            "project_id",
            "status",
            "started_at",
            "finished_at",
            "output_dir",
            "log_path",
            "command",
            "return_code",
            "error",
        )
        if _job_value(job, name) is not None
    }


def _repo_path(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def _wait_for_terminal(
    runtime: ArchitecturalOrchestrationRuntime,
    job_id: str,
    timeout_seconds: int,
) -> object:
    deadline = time.monotonic() + timeout_seconds
    while True:
        current = runtime.get(job_id)
        if current is None:
            raise RuntimeError(f"Authoritative runtime lost job {job_id}.")
        status = str(_job_value(current, "status", "UNKNOWN")).upper()
        if status not in {"QUEUED", "RUNNING"}:
            return current
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Authoritative runtime job {job_id} did not finish within {timeout_seconds}s."
            )
        time.sleep(1.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    parser.add_argument("--project-json", default="configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json")
    parser.add_argument("--runtime-root", default="projects/runtime")
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()
    repo = Path(args.repository).resolve()
    runtime_root = (repo / args.runtime_root).resolve()
    authoritative_root = (repo / "projects/runtime").resolve()
    if runtime_root != authoritative_root:
        raise ValueError("The authoritative runtime requires --runtime-root projects/runtime.")
    if args.timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be at least 1.")

    runtime = ArchitecturalOrchestrationRuntime(repo)
    started_job = runtime.start(args.project_json)
    job_id = str(_job_value(started_job, "job_id"))
    if not job_id or job_id == "None":
        raise RuntimeError("Authoritative runtime returned no job_id.")
    current_job = _wait_for_terminal(runtime, job_id, args.timeout_seconds)
    job_data = _job_dict(current_job)
    job_status = str(_job_value(current_job, "status", "UNKNOWN")).upper()
    log_value = _job_value(current_job, "log_path")
    if not log_value:
        raise RuntimeError("Authoritative runtime job returned no log_path.")
    log_path = _repo_path(repo, str(log_value))
    job_root = log_path.parent
    expected_jobs_root = runtime_root / "_architectural_orchestration_jobs"
    try:
        job_root.relative_to(expected_jobs_root)
    except ValueError as exc:
        raise RuntimeError("Authoritative runtime job path is outside its jobs root.") from exc
    bridge_root = job_root / "structural_session_bridge"
    bridge_result_path = bridge_root / "bridge_result.json"
    bridge_result = None
    if bridge_result_path.is_file():
        bridge_result = json.loads(bridge_result_path.read_text(encoding="utf-8-sig"))
        if str(bridge_result.get("job_id")) != job_id:
            raise RuntimeError("Structural bridge result job_id does not match the started job.")

    workspace = bridge_root / "workspace"
    if bridge_result and bridge_result.get("bridge_workspace"):
        reported_workspace = _repo_path(repo, bridge_result["bridge_workspace"])
        if reported_workspace != workspace.resolve():
            raise RuntimeError("Structural bridge reported an unexpected workspace path.")
    structural_output = (
        workspace / "results" / "session_adapters" / "structural_engineering"
        if workspace.is_dir() else None
    )
    package = None
    if structural_output:
        package = build_professional_review_package(
            repository=repo,
            workspace=workspace,
            output_dir=structural_output,
            project_id="MOSKEE-BUNSCHOTEN-E2E-REAL-001",
        )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    summary_path = runtime_root / "_professional_review_runs" / f"moskee_level_a_{timestamp}_{job_id}.json"
    summary = {
        "schema_version": "phoenix.moskee-level-a-professional-review-run/1.0",
        "project_id": "MOSKEE-BUNSCHOTEN-E2E-REAL-001",
        "authoritative_entrypoint": "ArchitecturalOrchestrationRuntime.start",
        "architectural_job": job_data,
        "architectural_job_id": job_id,
        "architectural_job_status": job_status,
        "architectural_job_root": str(job_root),
        "architectural_job_log": str(log_path),
        "bridge_result": str(bridge_result_path) if bridge_result_path.is_file() else None,
        "bridge_passed": bool(bridge_result and bridge_result.get("passed")),
        "bridge_return_code": bridge_result.get("return_code") if bridge_result else None,
        "workspace": str(workspace),
        "package_status": package.get("status") if package else "NOT_GENERATED",
        "package_manifest": str(package.get("manifest")) if package else None,
        "package_zip": str(package.get("zip")) if package else None,
        "missing_required_outputs": package.get("missing_required_outputs") if package else [],
        "design_package_state": "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW",
        "not_for_construction": True,
        "formal_release": "LOCKED",
        "professional_review_required": True,
        "automatic_professional_approval": False,
    }
    _write(summary_path, summary)
    print("MOSKEE_LEVEL_A_RUN_SUMMARY=" + str(summary_path))
    print("AUTHORITATIVE_ENTRYPOINT=ArchitecturalOrchestrationRuntime.start")
    print("ARCHITECTURAL_JOB_ID=" + job_id)
    print("ARCHITECTURAL_JOB_STATUS=" + job_status)
    print("ARCHITECTURAL_JOB_ROOT=" + str(job_root))
    print("ARCHITECTURAL_JOB_LOG=" + str(log_path))
    print("BRIDGE_RESULT=" + str(bridge_result_path))
    print("BRIDGE_PASSED=" + ("YES" if summary["bridge_passed"] else "NO"))
    print("BRIDGE_RETURN_CODE=" + str(summary["bridge_return_code"]))
    print("BRIDGE_WORKSPACE=" + str(workspace))
    print("PACKAGE_STATUS=" + summary["package_status"])
    print("PACKAGE_MANIFEST=" + str(summary["package_manifest"]))
    print("PACKAGE_ZIP=" + str(summary["package_zip"]))
    print("MISSING_REQUIRED_OUTPUTS=" + json.dumps(summary["missing_required_outputs"]))
    print("FORMAL_RELEASE=LOCKED")
    if bridge_result is None or not package:
        return 20
    if not bridge_result.get("passed"):
        return 10
    if package["status"] != "DESIGN_PACKAGE_FOR_PROFESSIONAL_REVIEW":
        return 10
    if job_status in {"FAILED", "ERROR", "CANCELLED", "CANCELED", "TIMED_OUT", "TIMEOUT"}:
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
