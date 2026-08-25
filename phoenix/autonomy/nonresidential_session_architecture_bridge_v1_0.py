"""Phoenix Level-A nonresidential project-context architecture bridge v1.0.

This module is deliberately a thin routing/compatibility layer.  It does not
generate a new nonresidential architecture.  For a selected project binding
that explicitly declares NONRESIDENTIAL_REUSE_V1, it reuses a tracked,
project-scoped canonical architectural model and exposes a lossless
Generic-Session-compatible `storeys` view.

Unknown/unrouted uses remain fail-closed and continue to the existing
architectural bootstrap behaviour.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

ROUTE_ID = "NONRESIDENTIAL_REUSE_V1"
SCHEMA_VERSION = "phoenix.nonresidential-session-architecture-context-bridge/1.0"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def _repo_path(repository: Path, value: str) -> Path:
    candidate = (repository / str(value).replace("\\", "/")).resolve()
    try:
        candidate.relative_to(repository.resolve())
    except ValueError as exc:
        raise ValueError(f"project reference escapes repository: {value}") from exc
    return candidate


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _route_contract(binding: dict[str, Any]) -> dict[str, Any] | None:
    for node in _walk_dicts(binding):
        if str(node.get("route") or "").strip().upper() == ROUTE_ID:
            return node
    return None


def _recursive_values(binding: dict[str, Any], keys: set[str]) -> list[str]:
    values: list[str] = []
    for node in _walk_dicts(binding):
        for key, value in node.items():
            if str(key).lower() in keys and isinstance(value, str) and value.strip():
                values.append(value.strip())
    return values


def _version_key(path: Path) -> tuple[int, ...]:
    match = re.search(r"_v(\d+)(?:_(\d+))?(?:_(\d+))?", path.stem, re.I)
    if not match:
        return (0,)
    return tuple(int(x or 0) for x in match.groups())


def _candidate_models(
    repository: Path,
    binding: dict[str, Any],
    route: dict[str, Any],
) -> list[Path]:
    explicit_keys = {
        "architectural_model",
        "architectural_model_file",
        "architectural_model_path",
        "canonical_architectural_model",
        "central_geometric_model",
        "central_geometric_model_file",
    }
    raw: list[Path] = []

    for value in _recursive_values(binding, explicit_keys):
        try:
            path = _repo_path(repository, value)
        except ValueError:
            continue
        if path.is_file() and path.suffix.lower() == ".json":
            raw.append(path)

    canonical_refs = []
    value = route.get("canonical_project_file")
    if isinstance(value, str) and value.strip():
        canonical_refs.append(value.strip())
    canonical_refs.extend(
        _recursive_values(binding, {"canonical_project_file"})
    )

    stems: list[str] = []
    for ref in canonical_refs:
        try:
            path = _repo_path(repository, ref)
        except ValueError:
            continue
        if path.is_file():
            stems.append(path.stem)

    project_dir = repository / "configs" / "projects"
    for stem in sorted(set(stems)):
        raw.extend(project_dir.glob(f"{stem}_architectural_model_*.json"))
        raw.extend(project_dir.glob(f"{stem}_central_geometric_model_*.json"))

    unique = {path.resolve(): path.resolve() for path in raw if path.is_file()}

    def priority(path: Path):
        name = path.name.lower()
        kind = 2 if "_architectural_model_" in name else 1
        return (kind, _version_key(path), name)

    return sorted(unique.values(), key=priority, reverse=True)


def _level_id(value: dict[str, Any], index: int) -> str:
    return str(
        value.get("storey_id")
        or value.get("level_id")
        or value.get("id")
        or f"L{index}"
    ).strip()


def _belongs(item: dict[str, Any], level_id: str) -> bool:
    ref = str(
        item.get("storey_id")
        or item.get("level_id")
        or item.get("level")
        or ""
    ).strip()
    return not ref or ref == level_id


def _opening_kind(item: dict[str, Any]) -> str:
    text = " ".join(
        str(item.get(key) or "")
        for key in ("type", "kind", "category", "name", "function")
    ).lower()
    if any(token in text for token in ("door", "deur", "entrance")):
        return "door"
    if any(token in text for token in ("window", "raam", "glazing")):
        return "window"
    return "opening"


def _lossless_storeys(model: dict[str, Any]) -> list[dict[str, Any]] | None:
    existing = model.get("storeys")
    if isinstance(existing, list) and existing:
        return copy.deepcopy(existing)

    levels = model.get("levels")
    if not isinstance(levels, list) or not levels:
        return None

    top_spaces = model.get("spaces") if isinstance(model.get("spaces"), list) else []
    top_walls = model.get("walls") if isinstance(model.get("walls"), list) else []
    top_openings = (
        model.get("openings") if isinstance(model.get("openings"), list) else []
    )
    top_stairs = model.get("stairs") if isinstance(model.get("stairs"), list) else []

    storeys: list[dict[str, Any]] = []
    for index, source_level in enumerate(levels):
        if not isinstance(source_level, dict):
            return None
        storey = copy.deepcopy(source_level)
        sid = _level_id(source_level, index)
        if not sid:
            return None

        storey["storey_id"] = sid
        storey.setdefault("id", sid)

        spaces = storey.get("spaces")
        if not isinstance(spaces, list):
            spaces = [copy.deepcopy(x) for x in top_spaces if isinstance(x, dict) and _belongs(x, sid)]
        for item in spaces:
            if isinstance(item, dict):
                item.setdefault("storey_id", sid)
                if item.get("id") and not item.get("space_id"):
                    item["space_id"] = item["id"]
        storey["spaces"] = spaces

        walls = storey.get("walls")
        if not isinstance(walls, list):
            walls = [copy.deepcopy(x) for x in top_walls if isinstance(x, dict) and _belongs(x, sid)]
        for item in walls:
            if isinstance(item, dict):
                item.setdefault("storey_id", sid)
                if item.get("id") and not item.get("element_id"):
                    item["element_id"] = item["id"]
        storey["walls"] = walls

        doors = storey.get("doors")
        windows = storey.get("windows")
        openings = storey.get("openings")
        if not isinstance(openings, list):
            openings = [
                copy.deepcopy(x)
                for x in top_openings
                if isinstance(x, dict) and _belongs(x, sid)
            ]
        if not isinstance(doors, list):
            doors = [copy.deepcopy(x) for x in openings if _opening_kind(x) == "door"]
        if not isinstance(windows, list):
            windows = [copy.deepcopy(x) for x in openings if _opening_kind(x) == "window"]
        for collection in (doors, windows, openings):
            for item in collection:
                if isinstance(item, dict):
                    item.setdefault("storey_id", sid)
        storey["doors"] = doors
        storey["windows"] = windows
        storey["openings"] = openings

        stairs = storey.get("stairs")
        if not isinstance(stairs, list):
            stairs = [copy.deepcopy(x) for x in top_stairs if isinstance(x, dict) and _belongs(x, sid)]
        for item in stairs:
            if isinstance(item, dict):
                item.setdefault("storey_id", sid)
        storey["stairs"] = stairs
        storeys.append(storey)

    return storeys


def _generic_view(
    source: dict[str, Any],
    *,
    session_project_id: str,
    binding_path: Path,
    source_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    storeys = _lossless_storeys(source)
    if not storeys:
        return None

    model = copy.deepcopy(source)
    source_project_id = model.get("project_id")
    model["storeys"] = storeys
    model["project_id"] = session_project_id
    model["project_binding_source"] = binding_path.as_posix()
    model["architectural_model_source"] = source_path.as_posix()
    model["architecture_route"] = ROUTE_ID
    model["compatibility_view"] = "LOSSLESS_LEVELS_TO_STOREYS"
    model["source_project_id"] = source_project_id
    model["candidate_only"] = True
    model["professional_review_required"] = True
    model["professional_approval"] = False
    model["production_release"] = "LOCKED"

    detailed = {
        "schema_version": "phoenix.nonresidential-generic-detailed-elements/1.0",
        "project_id": session_project_id,
        "architecture_route": ROUTE_ID,
        "source_model": source_path.as_posix(),
        "storeys": [
            {
                "storey_id": str(storey.get("storey_id") or storey.get("id")),
                "walls": copy.deepcopy(storey.get("walls") or []),
                "doors": copy.deepcopy(storey.get("doors") or []),
                "windows": copy.deepcopy(storey.get("windows") or []),
                "stairs": copy.deepcopy(storey.get("stairs") or []),
            }
            for storey in storeys
        ],
        "candidate_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    return model, detailed


def resolve_nonresidential_session_architecture(ctx: dict[str, Any]) -> dict[str, Any]:
    repository = Path(ctx["repository"]).resolve()
    session = ctx.get("session") or {}
    selected = str(
        session.get("selected_project")
        or session.get("project_file")
        or ""
    ).strip()

    if not selected:
        return {"matched": False, "status": "NOT_APPLICABLE"}

    try:
        binding_path = _repo_path(repository, selected)
    except ValueError as exc:
        return {
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_PATH_INVALID",
            "message": str(exc),
        }

    if not binding_path.is_file() or binding_path.suffix.lower() != ".json":
        return {"matched": False, "status": "NOT_APPLICABLE"}

    try:
        binding = _read_json(binding_path)
    except Exception as exc:
        return {
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_BINDING_INVALID",
            "message": str(exc),
        }

    route = _route_contract(binding)
    if route is None:
        return {"matched": False, "status": "NOT_APPLICABLE"}

    candidates = _candidate_models(repository, binding, route)
    if not candidates:
        return {
            "matched": True,
            "status": "BLOCKED",
            "reason": "NONRESIDENTIAL_CANONICAL_ARCHITECTURE_MODEL_REQUIRED",
            "message": (
                "NONRESIDENTIAL_REUSE_V1 is actief, maar geen getrackt "
                "projectgebonden architectuurmodel is gevonden."
            ),
        }

    failures: list[dict[str, str]] = []
    session_project_id = str(ctx.get("project_id") or "").strip()
    for source_path in candidates:
        try:
            source = _read_json(source_path)
            normalized = _generic_view(
                source,
                session_project_id=session_project_id,
                binding_path=binding_path,
                source_path=source_path,
            )
        except Exception as exc:
            failures.append({"path": source_path.as_posix(), "error": str(exc)})
            continue
        if normalized is None:
            failures.append(
                {
                    "path": source_path.as_posix(),
                    "error": "model has no usable levels/storeys collection",
                }
            )
            continue

        model, detailed = normalized
        evidence_path = Path(ctx["output_dir"]) / "nonresidential_route_context_bridge.json"
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASSED",
            "route": ROUTE_ID,
            "selected_project": selected,
            "binding_path": binding_path.as_posix(),
            "source_model": source_path.as_posix(),
            "source_model_sha256": __import__("hashlib").sha256(source_path.read_bytes()).hexdigest(),
            "storey_count": len(model["storeys"]),
            "session_project_id": session_project_id,
            "professional_approval": False,
            "production_release": "LOCKED",
            "for_construction": "LOCKED",
        }
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "matched": True,
            "status": "PASSED",
            "reason": None,
            "route": ROUTE_ID,
            "model_source_path": source_path,
            "detail_source_path": source_path,
            "model": model,
            "detailed_elements": detailed,
            "evidence_path": evidence_path,
        }

    return {
        "matched": True,
        "status": "BLOCKED",
        "reason": "NONRESIDENTIAL_CANONICAL_ARCHITECTURE_MODEL_INCOMPATIBLE",
        "message": (
            "Projectgebonden architectuurmodellen zijn gevonden maar konden niet "
            "lossless naar de Generic Session storeys-view worden vertaald."
        ),
        "failures": failures,
    }
