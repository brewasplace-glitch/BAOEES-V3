from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

REQS = ("REQ-102","REQ-103","REQ-104","REQ-105","REQ-106","REQ-108")
ALLOWED = {".pdf",".docx",".xlsx",".csv",".json",".ifc",".dwg",".dxf",".png",".jpg",".jpeg"}

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(args, *, cwd=None, timeout=7200) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(x) for x in args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )

def execute_closure_prerequisite(
    repository: Path,
    project: Path,
    output: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    script = (
        repository
        / "runners"
        / "PROJECT_PHOENIX_professional_evidence_closure_engine_v6_3_0.py"
    )
    cp = run(
        [
            sys.executable,
            script,
            "--repository", repository,
            "--project", project,
            "--output", output,
            "--evidence-root", evidence_root,
        ],
        cwd=repository,
    )
    (output.parent / "closure_stdout.txt").write_text(
        cp.stdout or "", encoding="utf-8"
    )
    (output.parent / "closure_stderr.txt").write_text(
        cp.stderr or "", encoding="utf-8"
    )
    summary = output / "evidence_closure_run.json"
    if cp.returncode != 0 or not summary.is_file():
        raise RuntimeError(
            f"v6.3.1 evidence closure prerequisite failed: {cp.returncode}"
        )
    data = read_json(summary)
    if (
        data.get("status") != "PASSED"
        or data.get("requirements_evaluated") != 6
        or data.get("automatic_approval") is not False
    ):
        raise RuntimeError("v6.3.1 evidence closure prerequisite is invalid")
    return data

def ensure_structure(evidence_root: Path) -> None:
    for req in REQS:
        (evidence_root / req / "sources").mkdir(parents=True, exist_ok=True)
        (evidence_root / req / "metadata").mkdir(parents=True, exist_ok=True)
        (evidence_root / req / "review").mkdir(parents=True, exist_ok=True)
        (evidence_root / req / "review_packets").mkdir(parents=True, exist_ok=True)

def valid_metadata(path: Path, source_file: Path) -> tuple[bool, dict[str, Any] | None]:
    if not path.is_file():
        return False, None
    try:
        data = read_json(path)
    except Exception:
        return False, None
    required = (
        "source_id",
        "source_title",
        "source_date",
        "source_version",
        "origin",
        "discipline",
        "file_name",
    )
    valid = all(data.get(key) for key in required)
    valid = valid and data.get("file_name") == source_file.name
    return bool(valid), data

def scan_requirement(req: str, evidence_root: Path) -> dict[str, Any]:
    req_root = evidence_root / req
    source_dir = req_root / "sources"
    metadata_dir = req_root / "metadata"
    review_dir = req_root / "review"

    sources = []
    invalid_files = []
    metadata_missing = []
    hashes = {}
    duplicate_hashes = []

    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED or path.stat().st_size == 0:
            invalid_files.append(path.name)
            continue

        digest = sha256(path)
        if digest in hashes:
            duplicate_hashes.append({
                "file": path.name,
                "duplicate_of": hashes[digest],
                "sha256": digest,
            })
        else:
            hashes[digest] = path.name

        metadata_path = metadata_dir / f"{path.name}.metadata.json"
        metadata_ok, metadata = valid_metadata(metadata_path, path)
        if not metadata_ok:
            metadata_missing.append(path.name)

        sources.append({
            "file_name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": digest,
            "metadata_status": "VALID" if metadata_ok else "MISSING_OR_INVALID",
            "metadata": metadata,
        })

    assignment_path = review_dir / "reviewer_assignment.json"
    assignment = None
    assignment_valid = False
    if assignment_path.is_file():
        try:
            assignment = read_json(assignment_path)
            assignment_valid = bool(
                assignment.get("requirement_id") == req
                and assignment.get("reviewer_name")
                and assignment.get("reviewer_role")
                and assignment.get("reviewer_organization")
                and assignment.get("assignment_date")
            )
        except Exception:
            assignment = None

    decision_path = review_dir / "professional_review.json"
    decision = None
    decision_valid = False
    if decision_path.is_file():
        try:
            decision = read_json(decision_path)
            decision_valid = bool(
                decision.get("requirement_id") == req
                and decision.get("reviewer", {}).get("name")
                and decision.get("reviewer", {}).get("role")
                and decision.get("reviewer", {}).get("organization")
                and decision.get("review_date")
                and decision.get("decision")
                in {"APPROVED", "REJECTED", "REVISION_REQUIRED"}
            )
        except Exception:
            decision = None

    if not sources:
        state = "EMPTY"
    elif invalid_files or metadata_missing or duplicate_hashes:
        state = "METADATA_INCOMPLETE"
    elif not assignment_valid:
        state = "INTAKE_RECEIVED"
    elif not decision_valid:
        state = "READY_FOR_REVIEW"
    elif decision["decision"] == "APPROVED":
        state = "APPROVED"
    elif decision["decision"] == "REJECTED":
        state = "REJECTED"
    else:
        state = "REVISION_REQUIRED"

    return {
        "requirement_id": req,
        "state": state,
        "source_count": len(sources),
        "sources": sources,
        "invalid_files": invalid_files,
        "metadata_missing_or_invalid": metadata_missing,
        "duplicate_hashes": duplicate_hashes,
        "reviewer_assignment": {
            "status": "VALID" if assignment_valid else "MISSING_OR_INVALID",
            "record": assignment,
        },
        "professional_review": {
            "status": "VALID" if decision_valid else "NOT_REVIEWED",
            "record": decision,
        },
        "automatic_approval": False,
    }

def create_review_packet(
    req: str,
    result: dict[str, Any],
    packet_dir: Path,
    project_id: str,
) -> Path:
    packet = {
        "schema_version": "phoenix.evidence-review-packet/6.4.0",
        "project_id": project_id,
        "requirement_id": req,
        "workflow_state": result["state"],
        "sources": result["sources"],
        "intake_issues": {
            "invalid_files": result["invalid_files"],
            "metadata_missing_or_invalid": result[
                "metadata_missing_or_invalid"
            ],
            "duplicate_hashes": result["duplicate_hashes"],
        },
        "reviewer_assignment": result["reviewer_assignment"],
        "professional_review": result["professional_review"],
        "automatic_approval": False,
    }
    packet_path = packet_dir / f"{req}_review_packet.json"
    write_json(packet_path, packet)
    return packet_path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository", default=".")
    ap.add_argument("--project", required=True)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    repository = Path(args.repository).resolve()
    project_path = Path(args.project).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    output = Path(args.output).resolve()

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    ensure_structure(evidence_root)
    project = read_json(project_path)
    write_json(output / "project_manifest_snapshot.json", project)

    closure_output = output / "closure_prerequisite"
    execute_closure_prerequisite(
        repository,
        project_path,
        closure_output,
        evidence_root,
    )

    results = {}
    packet_records = []
    for req in REQS:
        result = scan_requirement(req, evidence_root)
        results[req] = result
        packet = create_review_packet(
            req,
            result,
            output / "review_packets",
            project["project_id"],
        )
        packet_records.append({
            "requirement_id": req,
            "path": packet.relative_to(output).as_posix(),
            "sha256": sha256(packet),
        })
        write_json(output / "requirements" / f"{req}_workflow.json", result)

    approved = [r for r in REQS if results[r]["state"] == "APPROVED"]
    req108_ready = all(results[r]["state"] == "APPROVED" for r in REQS[:-1])
    closed = list(approved)
    if "REQ-108" in closed and not req108_ready:
        closed.remove("REQ-108")
        results["REQ-108"]["state"] = "REVISION_REQUIRED"
        results["REQ-108"]["dependency_issue"] = (
            "REQ-102 through REQ-106 must be approved first"
        )
        write_json(
            output / "requirements" / "REQ-108_workflow.json",
            results["REQ-108"],
        )

    open_reqs = [r for r in REQS if r not in closed]
    permit_ready = len(closed) == len(REQS)

    dashboard = {
        "schema_version": "phoenix.evidence-workflow-dashboard/6.4.0",
        "project_id": project["project_id"],
        "requirement_count": len(REQS),
        "approved_count": len(closed),
        "open_count": len(open_reqs),
        "permit_ready": permit_ready,
        "requirements": {
            req: {
                "state": results[req]["state"],
                "source_count": results[req]["source_count"],
                "assignment_status": results[req][
                    "reviewer_assignment"
                ]["status"],
                "review_status": results[req][
                    "professional_review"
                ]["status"],
            }
            for req in REQS
        },
    }
    write_json(output / "evidence_workflow_dashboard.json", dashboard)

    missing = {
        req: {
            "state": results[req]["state"],
            "invalid_files": results[req]["invalid_files"],
            "metadata_missing_or_invalid": results[req][
                "metadata_missing_or_invalid"
            ],
            "reviewer_assignment": results[req][
                "reviewer_assignment"
            ]["status"],
            "professional_review": results[req][
                "professional_review"
            ]["status"],
        }
        for req in open_reqs
    }
    write_json(output / "missing_evidence_and_actions.json", missing)

    twin = read_json(
        closure_output / "digital_twin_v6_3_0.json"
    )
    twin["schema_version"] = "phoenix.digital-twin-project/6.4.0"
    twin["evidence_intake_review_workflow"] = results
    twin["release"] = {
        "status": "PERMIT_READY" if permit_ready
        else "BLOCKED_PENDING_EVIDENCE_AND_REVIEW",
        "permit_ready": permit_ready,
        "closed_requirements": closed,
        "open_requirements": open_reqs,
        "automatic_professional_approval": False,
    }
    write_json(output / "digital_twin_v6_4_0.json", twin)

    artifacts = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({
                "path": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    write_json(output / "artifact_manifest.json", {
        "schema_version": "phoenix.evidence-workflow-artifacts/6.4.0",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    })

    write_json(output / "evidence_workflow_run.json", {
        "schema_version": "phoenix.evidence-workflow-run/6.4.0",
        "status": "PASSED",
        "project_id": project["project_id"],
        "requirements_processed": len(REQS),
        "review_packets_generated": len(packet_records),
        "requirements_approved": len(closed),
        "requirements_open": len(open_reqs),
        "automatic_approval": False,
        "permit_ready": permit_ready,
    })

    write_json(output / "permit_ready_release_gate.json", {
        "schema_version": "phoenix.evidence-workflow-release-gate/6.4.0",
        "status": "UNLOCKED" if permit_ready else "LOCKED",
        "permit_ready": permit_ready,
        "closed_requirements": closed,
        "open_requirements": open_reqs,
        "automatic_professional_approval": False,
    })

    print("PROFESSIONAL EVIDENCE INTAKE AND REVIEW WORKFLOW: PASSED")
    print("EVIDENCE INTAKE STRUCTURE: VERIFIED")
    print("REQUIREMENT REVIEW PACKETS GENERATED: 6")
    print("DUPLICATE HASH DETECTION: ACTIVE")
    print("PROFESSIONAL REVIEW ASSIGNMENT: REQUIRED")
    print("AUTOMATIC PROFESSIONAL APPROVAL: DISABLED")
    print("CENTRAL DIGITAL TWIN REVIEW WRITEBACK: PASSED")
    print(
        "PERMIT-READY RELEASE GATE: "
        + ("UNLOCKED" if permit_ready else "LOCKED")
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
