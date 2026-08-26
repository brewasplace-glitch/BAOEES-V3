"""Project Phoenix Level-A Candidate Project ZIP Artifact Bridge v1.0.

Creates a deterministic project evidence package from the current project workspace.
This artifact is a Level-A candidate package only. It never implies professional
approval, permit readiness, production release, or FOR CONSTRUCTION status.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
ARCHIVE_NAME = "project_level_a_candidate_package.zip"
SIDECAR_NAME = "project_level_a_candidate_package_manifest.json"
INTERNAL_MANIFEST_NAME = "PROJECT_ZIP_MANIFEST.json"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _candidate_files(workspace: Path, output_dir: Path) -> list[Path]:
    archive = (output_dir / ARCHIVE_NAME).resolve()
    sidecar = (output_dir / SIDECAR_NAME).resolve()
    result: list[Path] = []

    for path in workspace.rglob("*"):
        if not path.is_file():
            continue

        resolved = path.resolve()
        if resolved in {archive, sidecar}:
            continue

        # Never recursively package earlier/current project archives.
        if path.suffix.lower() == ".zip":
            continue

        # Ignore transient filesystem files only; retain actual project evidence.
        if path.name.lower() in {"thumbs.db", ".ds_store"}:
            continue
        if path.suffix.lower() in {".tmp", ".lock"}:
            continue

        result.append(path)

    return sorted(result, key=lambda p: p.relative_to(workspace).as_posix())


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def emit_level_a_project_zip_artifact(
    *,
    workspace: Path,
    output_dir: Path,
    project_id: str,
    session_id: str | None,
    qaqc_gate_path: Path | None = None,
) -> tuple[Path, Path]:
    """Emit deterministic candidate ZIP + sidecar manifest.

    The package may be generated while QA/QC is still blocked because packaging
    evidence is independent from formal engineering approval. The safety state is
    carried explicitly in both the internal and sidecar manifests.
    """

    workspace = Path(workspace).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not workspace.is_dir():
        raise ValueError(f"Project workspace does not exist: {workspace}")

    try:
        output_dir.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("Project ZIP output_dir must be inside project workspace") from exc

    archive_path = output_dir / ARCHIVE_NAME
    sidecar_path = output_dir / SIDECAR_NAME
    files = _candidate_files(workspace, output_dir)

    gate_state: dict[str, Any] = {
        "qaqc_status": "UNKNOWN",
        "upstream_blocker_count": None,
    }
    if qaqc_gate_path is not None and Path(qaqc_gate_path).is_file():
        try:
            gate = json.loads(Path(qaqc_gate_path).read_text(encoding="utf-8-sig"))
            if isinstance(gate, dict):
                gate_state = {
                    "qaqc_status": gate.get("qaqc_status"),
                    "upstream_blocker_count": gate.get("upstream_blocker_count"),
                }
        except Exception:
            gate_state = {
                "qaqc_status": "UNREADABLE",
                "upstream_blocker_count": None,
            }

    entries = [
        {
            "path": path.relative_to(workspace).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    ]

    internal_manifest = {
        "schema_version": "phoenix.level-a-project-zip-artifact/1.0",
        "engine_version": VERSION,
        "artifact_type": "PROJECT_ZIP",
        "package_class": "LEVEL_A_CANDIDATE_PROJECT_EVIDENCE",
        "project_id": project_id,
        "session_id": session_id,
        "payload_entry_count": len(entries),
        "payload_entries": entries,
        "qaqc_gate_state": gate_state,
        "formal_release": False,
        "professional_review_required": True,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
        "for_construction": "LOCKED",
    }
    manifest_bytes = _json_bytes(internal_manifest)

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        archive.writestr(_zip_info(INTERNAL_MANIFEST_NAME), manifest_bytes)
        for path in files:
            relative = path.relative_to(workspace).as_posix()
            archive.writestr(_zip_info(relative), path.read_bytes())

    if not zipfile.is_zipfile(archive_path):
        raise RuntimeError("Generated project ZIP is not a valid ZIP archive")

    with zipfile.ZipFile(archive_path, mode="r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"Generated project ZIP failed integrity check: {bad_member}")
        names = archive.namelist()

    sidecar = {
        "schema_version": "phoenix.level-a-project-zip-artifact-manifest/1.0",
        "engine_version": VERSION,
        "artifact_type": "PROJECT_ZIP",
        "package_class": "LEVEL_A_CANDIDATE_PROJECT_EVIDENCE",
        "project_id": project_id,
        "session_id": session_id,
        "archive": archive_path.name,
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": _sha256(archive_path),
        "archive_entry_count": len(names),
        "internal_manifest": INTERNAL_MANIFEST_NAME,
        "qaqc_gate_state": gate_state,
        "formal_release": False,
        "professional_review_required": True,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
        "for_construction": "LOCKED",
    }
    _write_json(sidecar_path, sidecar)

    return archive_path, sidecar_path
