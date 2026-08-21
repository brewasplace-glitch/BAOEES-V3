"""Bounded canonical-v4 -> Generic Session / v8.0 compatibility bridge.

This module is intentionally bridge-local. It does not redefine the authoritative
architectural model. It derives a compatibility view from the selected A-E canonical
variant and preserves provenance/release locks.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phoenix.autonomy.session_orchestrator import AutonomousProjectOrchestrator


VERSION = "1.0.0"
SCHEMA = "phoenix.canonical-v4-to-generic-storey-bridge/1.0"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_ref(path: Path, repository: Path) -> str:
    return Path(path).resolve().relative_to(Path(repository).resolve()).as_posix()


def _safe_token(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._")
    return value[:80] or "bridge"


def _euclidean_length(start: Any, end: Any) -> float | None:
    if (
        isinstance(start, list)
        and isinstance(end, list)
        and len(start) >= 2
        and len(end) >= 2
    ):
        try:
            dx = float(end[0]) - float(start[0])
            dy = float(end[1]) - float(start[1])
            return round(math.hypot(dx, dy), 6)
        except (TypeError, ValueError):
            return None
    return None


def _rectangular_bbox(polygon: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(polygon, list) or len(polygon) < 4:
        return None

    points: list[tuple[float, float]] = []
    try:
        for point in polygon:
            if not isinstance(point, list) or len(point) < 2:
                return None
            points.append((float(point[0]), float(point[1])))
    except (TypeError, ValueError):
        return None

    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) != 4:
        return None

    xs = sorted({round(point[0], 9) for point in points})
    ys = sorted({round(point[1], 9) for point in points})
    if len(xs) != 2 or len(ys) != 2:
        return None

    expected = {
        (xs[0], ys[0]),
        (xs[1], ys[0]),
        (xs[1], ys[1]),
        (xs[0], ys[1]),
    }
    actual = {(round(x, 9), round(y, 9)) for x, y in points}
    if actual != expected:
        return None

    return (xs[0], ys[0], round(xs[1] - xs[0], 6), round(ys[1] - ys[0], 6))


def select_recommended_canonical_source(
    repository: Path,
    project_runtime: Path,
) -> tuple[Path, str, dict[str, Any]]:
    repository = Path(repository).resolve()
    project_runtime = Path(project_runtime).resolve()
    manifest_path = (
        project_runtime
        / "delivery"
        / "nonresidential_reuse_v1"
        / "delivery_manifest.json"
    )
    if not manifest_path.is_file():
        raise RuntimeError("Nonresidential delivery manifest ontbreekt voor structural bridge.")

    manifest = _read_json(manifest_path)
    recommended = str(manifest.get("recommended_variant_id") or "").strip()
    if not recommended:
        raise RuntimeError("recommended_variant_id ontbreekt in delivery manifest.")

    candidates = [
        (
            project_runtime
            / "delivery"
            / "nonresidential_reuse_v1"
            / "variants"
            / f"variant_{recommended}"
            / "canonical_architectural_model.json"
        ),
        (
            project_runtime
            / "delivery"
            / "nonresidential_reuse_v1"
            / "variants"
            / f"variant_{recommended}"
            / "suite"
            / "01_canonical_architectural_model.json"
        ),
    ]

    for path in candidates:
        if not path.is_file():
            continue
        value = _read_json(path)
        levels = value.get("levels")
        walls = value.get("walls")
        spaces = value.get("spaces")
        openings = value.get("openings")
        if (
            isinstance(levels, list)
            and len(levels) > 0
            and isinstance(walls, list)
            and len(walls) > 0
            and isinstance(spaces, list)
            and isinstance(openings, list)
        ):
            return path, recommended, value

    raise RuntimeError(
        "Aanbevolen A-E variant bevat geen bruikbaar canonical levels/walls/spaces/openings contract."
    )


def normalize_canonical_v4_for_structural_session(
    canonical: dict[str, Any],
    *,
    project_id: str,
    source_path: Path,
    recommended_variant_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    levels = canonical.get("levels")
    walls = canonical.get("walls")
    spaces = canonical.get("spaces")
    openings = canonical.get("openings")
    if not (
        isinstance(levels, list)
        and levels
        and isinstance(walls, list)
        and walls
        and isinstance(spaces, list)
        and isinstance(openings, list)
    ):
        raise RuntimeError("Canonical v4 relationship contract is onvolledig.")

    level_ids: list[str] = []
    for level in levels:
        if not isinstance(level, dict) or not str(level.get("id") or "").strip():
            raise RuntimeError("Canonical level zonder geldige id.")
        level_ids.append(str(level["id"]))
    if len(level_ids) != len(set(level_ids)):
        raise RuntimeError("Dubbele canonical level-id.")

    wall_by_id: dict[str, dict[str, Any]] = {}
    for wall in walls:
        if not isinstance(wall, dict):
            raise RuntimeError("Canonical wall moet een object zijn.")
        wall_id = str(wall.get("id") or "").strip()
        level_id = str(wall.get("level_id") or "").strip()
        if not wall_id or wall_id in wall_by_id:
            raise RuntimeError("Canonical wall-id ontbreekt of is dubbel.")
        if level_id not in level_ids:
            raise RuntimeError(f"Wall {wall_id} verwijst naar onbekend level {level_id!r}.")
        wall_by_id[wall_id] = wall

    for space in spaces:
        if not isinstance(space, dict):
            raise RuntimeError("Canonical space moet een object zijn.")
        level_id = str(space.get("level_id") or "").strip()
        if level_id not in level_ids:
            raise RuntimeError(
                f"Space {space.get('id')!r} verwijst naar onbekend level {level_id!r}."
            )

    opening_level: dict[str, str] = {}
    for opening in openings:
        if not isinstance(opening, dict):
            raise RuntimeError("Canonical opening moet een object zijn.")
        opening_id = str(opening.get("id") or "UNKNOWN")
        wall_id = str(opening.get("wall_id") or "").strip()
        wall = wall_by_id.get(wall_id)
        if wall is None:
            raise RuntimeError(
                f"Opening {opening_id} verwijst naar onbekende wall {wall_id!r}."
            )
        opening_level[opening_id] = str(wall["level_id"])

    normalized = copy.deepcopy(canonical)
    normalized["source_project_id"] = canonical.get("project_id")
    normalized["project_id"] = str(project_id)
    normalized["storeys"] = []
    normalized["candidate_only"] = True
    normalized["professional_review_required"] = True
    normalized["production_release"] = "LOCKED"
    normalized["for_construction"] = "LOCKED"

    source_path = Path(source_path).resolve()
    normalized["bridge_provenance"] = {
        "schema_version": SCHEMA,
        "bridge_version": VERSION,
        "source_path": str(source_path),
        "source_sha256": _sha256(source_path),
        "recommended_variant_id": str(recommended_variant_id),
        "original_canonical_fields_preserved": True,
        "geometry_values_copied_not_invented": True,
        "identity_aliases": {
            "storey.storey_id": "storey.id",
            "wall.element_id": "wall.id",
            "wall.storey_id": "wall.level_id",
            "space.element_id": "space.id",
            "space.space_id": "space.id",
            "space.storey_id": "space.level_id",
        },
        "derived_geometry": {
            "wall.length_m": "euclidean(wall.start, wall.end)",
            "wall.category": "external boolean -> external_wall/internal_wall",
            "space.x_y_width_depth": "axis-aligned rectangular polygon bbox only",
        },
        "production_release": "LOCKED",
        "for_construction": "LOCKED",
    }

    by_level: dict[str, dict[str, Any]] = {}
    for level in levels:
        level_id = str(level["id"])
        storey = copy.deepcopy(level)
        storey["storey_id"] = level_id
        storey["walls"] = []
        storey["spaces"] = []
        storey["doors"] = []
        storey["windows"] = []
        storey["other_openings"] = []
        normalized["storeys"].append(storey)
        by_level[level_id] = storey

    stats = {
        "storey_count": len(levels),
        "wall_count": 0,
        "space_count": 0,
        "door_count": 0,
        "window_count": 0,
        "other_opening_count": 0,
        "wall_length_derived_count": 0,
        "wall_category_derived_count": 0,
        "space_bbox_derived_count": 0,
    }

    for wall in walls:
        value = copy.deepcopy(wall)
        value["element_id"] = str(value["id"])
        value["storey_id"] = str(value["level_id"])

        if "length_m" not in value:
            length = _euclidean_length(value.get("start"), value.get("end"))
            if length is None or length <= 0:
                raise RuntimeError(
                    f"Wall {value['id']} heeft geen veilig afleidbare positieve lengte."
                )
            value["length_m"] = length
            stats["wall_length_derived_count"] += 1

        if "category" not in value:
            external = value.get("external")
            if not isinstance(external, bool):
                raise RuntimeError(
                    f"Wall {value['id']} mist boolean external voor veilige category-afleiding."
                )
            value["category"] = "external_wall" if external else "internal_wall"
            stats["wall_category_derived_count"] += 1

        by_level[value["storey_id"]]["walls"].append(value)
        stats["wall_count"] += 1

    for space in spaces:
        value = copy.deepcopy(space)
        space_id = str(value.get("id") or "").strip()
        if not space_id:
            raise RuntimeError("Canonical space zonder geldige id.")
        value["element_id"] = space_id
        value["space_id"] = space_id
        value["storey_id"] = str(value["level_id"])

        required = {"x_m", "y_m", "width_m", "depth_m"}
        if not required.issubset(value):
            bbox = _rectangular_bbox(value.get("polygon"))
            if bbox is None:
                raise RuntimeError(
                    f"Space {space_id} is niet axis-aligned rechthoekig; "
                    "Phoenix mag hiervoor geen v8.0 bbox verzinnen."
                )
            x_m, y_m, width_m, depth_m = bbox
            value.setdefault("x_m", x_m)
            value.setdefault("y_m", y_m)
            value.setdefault("width_m", width_m)
            value.setdefault("depth_m", depth_m)
            stats["space_bbox_derived_count"] += 1

        if float(value["width_m"]) <= 0 or float(value["depth_m"]) <= 0:
            raise RuntimeError(f"Space {space_id} heeft niet-positieve afmetingen.")

        by_level[value["storey_id"]]["spaces"].append(value)
        stats["space_count"] += 1

    for opening in openings:
        value = copy.deepcopy(opening)
        opening_id = str(value.get("id") or "UNKNOWN")
        level_id = opening_level[opening_id]
        value["element_id"] = opening_id
        value["storey_id"] = level_id
        kind = str(value.get("kind") or "").strip().lower()
        if kind == "door":
            by_level[level_id]["doors"].append(value)
            stats["door_count"] += 1
        elif kind == "window":
            by_level[level_id]["windows"].append(value)
            stats["window_count"] += 1
        else:
            by_level[level_id]["other_openings"].append(value)
            stats["other_opening_count"] += 1

    return normalized, stats


def prepare_isolated_structural_bridge(
    *,
    repository: Path,
    project_runtime: Path,
    bridge_root: Path,
    session: dict[str, Any],
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    project_runtime = Path(project_runtime).resolve()
    bridge_root = Path(bridge_root).resolve()
    bridge_root.mkdir(parents=True, exist_ok=True)

    source_path, recommended, canonical = select_recommended_canonical_source(
        repository, project_runtime
    )
    normalized, stats = normalize_canonical_v4_for_structural_session(
        canonical,
        project_id=str(session.get("selected_project") or project_runtime.name),
        source_path=source_path,
        recommended_variant_id=recommended,
    )

    # Verify against the live Generic Session Adapter contract before execution.
    from phoenix.autonomy import session_adapters

    if not session_adapters._architecture_model_candidate(normalized):
        raise RuntimeError("Bridge-normalized model faalt Generic architecture model gate.")
    if not session_adapters._detailed_elements_candidate(normalized):
        raise RuntimeError("Bridge-normalized model faalt Generic detailed-elements gate.")

    batch_id = "structural_bridge_" + _safe_token(
        str(session.get("session_id") or bridge_root.name)
    )
    upload_root = (
        repository
        / "inputs"
        / "runtime"
        / "official_start_v3_uploads"
        / batch_id
    )
    if upload_root.exists():
        shutil.rmtree(upload_root)
    upload_root.mkdir(parents=True, exist_ok=False)

    normalized_upload = upload_root / "canonical_v4_structural_bridge_model.json"
    _write_json(normalized_upload, normalized)
    _write_json(
        upload_root / "upload_manifest.json",
        {
            "schema_version": "phoenix.structural-bridge-upload-manifest/1.0",
            "batch_id": batch_id,
            "project_id": session.get("selected_project"),
            "source_path": str(source_path),
            "source_sha256": _sha256(source_path),
            "normalized_file": normalized_upload.name,
            "normalized_sha256": _sha256(normalized_upload),
            "recommended_variant_id": recommended,
            "stats": stats,
            "production_release": "LOCKED",
            "for_construction": "LOCKED",
        },
    )
    session["upload_batch"] = batch_id

    workspace = bridge_root / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / "digital_twin").mkdir(parents=True, exist_ok=True)
    (workspace / "orchestration").mkdir(parents=True, exist_ok=True)

    project_id = str(session.get("selected_project") or project_runtime.name)
    orchestrator = AutonomousProjectOrchestrator(repository)
    plan = orchestrator.build_plan(session, project_id)

    release = {
        "production_acceptance_test": "PENDING",
        "production_release": "LOCKED",
        "automatic_professional_approval": False,
    }
    manifest_path = workspace / "project_manifest.json"
    twin_path = workspace / "digital_twin" / "project_state.json"
    plan_path = workspace / "orchestration" / "dependency_plan.json"

    _write_json(
        manifest_path,
        {
            "schema_version": "phoenix.autonomous-project-manifest/1.0",
            "orchestrator_version": orchestrator.VERSION,
            "project_id": project_id,
            "project_type": session.get("project_type"),
            "project_mode": session.get("project_mode"),
            "brief": session.get("brief"),
            "selected_project": session.get("selected_project"),
            "desired_outputs": session.get("desired_outputs", []),
            "session_id": session.get("session_id"),
            "upload": {
                "batch_id": batch_id,
                "manifest": _repo_ref(
                    upload_root / "upload_manifest.json", repository
                ),
                "available": True,
            },
            "bridge_source": {
                "canonical_model": str(source_path),
                "canonical_sha256": _sha256(source_path),
                "normalized_upload": _repo_ref(normalized_upload, repository),
                "normalized_sha256": _sha256(normalized_upload),
                "recommended_variant_id": recommended,
                "stats": stats,
            },
            "release": release,
        },
    )
    _write_json(
        twin_path,
        {
            "schema_version": "phoenix.digital-twin-project-state/1.0",
            "project_id": project_id,
            "session_id": session.get("session_id"),
            "state": "BOOTSTRAPPED",
            "source_of_truth": "project_manifest.json",
            "disciplines": {},
            "desired_outputs": session.get("desired_outputs", []),
            "release": release,
        },
    )
    _write_json(plan_path, plan)

    session["bootstrap"] = {
        "project_id": project_id,
        "workspace": _repo_ref(workspace, repository),
        "project_manifest": _repo_ref(manifest_path, repository),
        "digital_twin_state": _repo_ref(twin_path, repository),
        "orchestration_plan": _repo_ref(plan_path, repository),
    }
    session.setdefault("bridge", {})
    if isinstance(session["bridge"], dict):
        session["bridge"].update(
            {
                "schema_compatibility": SCHEMA,
                "bridge_workspace": _repo_ref(workspace, repository),
                "source_canonical_model": str(source_path),
                "source_canonical_sha256": _sha256(source_path),
                "normalized_upload": _repo_ref(normalized_upload, repository),
                "normalized_upload_sha256": _sha256(normalized_upload),
                "recommended_variant_id": recommended,
                "normalization_stats": stats,
                "primary_ae_workspace_overwrite": False,
                "production_release": "LOCKED",
                "for_construction": "LOCKED",
            }
        )

    return {
        "batch_id": batch_id,
        "upload_root": upload_root,
        "workspace": workspace,
        "source_path": source_path,
        "source_sha256": _sha256(source_path),
        "normalized_upload": normalized_upload,
        "normalized_sha256": _sha256(normalized_upload),
        "recommended_variant_id": recommended,
        "stats": stats,
    }


def cleanup_bridge_upload(preparation: dict[str, Any]) -> None:
    root = Path(preparation["upload_root"])
    if root.exists():
        shutil.rmtree(root)


def publish_structural_bridge_outputs(
    *,
    repository: Path,
    project_runtime: Path,
    preparation: dict[str, Any],
    runner_return_code: int,
    session_id: str,
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    project_runtime = Path(project_runtime).resolve()
    workspace = Path(preparation["workspace"]).resolve()

    source_dir = (
        workspace / "results" / "session_adapters" / "structural_engineering"
    )
    isolated_inp = sorted(source_dir.rglob("*.inp")) if source_dir.is_dir() else []

    published_dir = (
        project_runtime / "results" / "session_adapters" / "structural_engineering"
    )
    published = False

    # Publish only when this isolated run has genuine structural artifacts. A
    # blocked later v8.x stage may still have valid solver-input evidence; the
    # bridge result remains blocked unless the general runner itself returned 0.
    if source_dir.is_dir() and isolated_inp:
        if published_dir.exists():
            shutil.rmtree(published_dir)
        published_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, published_dir)
        published = True

        _write_json(
            published_dir / "bridge_publication_manifest.json",
            {
                "schema_version": "phoenix.structural-bridge-publication/1.0",
                "session_id": session_id,
                "runner_return_code": int(runner_return_code),
                "isolated_workspace": _repo_ref(workspace, repository),
                "source_canonical_model": str(preparation["source_path"]),
                "source_canonical_sha256": preparation["source_sha256"],
                "normalized_sha256": preparation["normalized_sha256"],
                "recommended_variant_id": preparation["recommended_variant_id"],
                "isolated_inp_count": len(isolated_inp),
                "production_release": "LOCKED",
                "for_construction": "LOCKED",
            },
        )

    published_inp = (
        sorted(published_dir.rglob("*.inp")) if published_dir.is_dir() else []
    )
    return {
        "isolated_structural_adapter_dir": source_dir,
        "isolated_inp": isolated_inp,
        "published_structural_adapter_dir": published_dir,
        "published_inp": published_inp,
        "published": published,
    }
