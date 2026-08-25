"""Selected-project explicit context bridge for Project Phoenix.

Reads explicit project facts from the selected project JSON and exposes only
non-inferred facts to the autonomous project context.  It is a routing bridge,
not a geocoder and not a legal/jurisdiction engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "phoenix.selected-project-context-bridge/1.0"

# Conservative ISO aliases for jurisdictions already used by Phoenix projects.
# Unknown names are never guessed.
_COUNTRY_CODE_ALIASES = {
    "nl": "NL",
    "nederland": "NL",
    "netherlands": "NL",
    "sr": "SR",
    "suriname": "SR",
}


def _repo_path(repository: Path, value: str) -> Path:
    candidate = (repository / value.replace("\\", "/")).resolve()
    candidate.relative_to(repository.resolve())
    return candidate


def _first_string(obj: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _country_code(obj: dict[str, Any], country_name: str | None) -> str | None:
    explicit = _first_string(obj, ("country_code", "iso_country_code", "country_iso2"))
    if explicit:
        code = explicit.strip().upper()
        if len(code) == 2 and code.isalpha():
            return code
        return None
    if country_name:
        return _COUNTRY_CODE_ALIASES.get(country_name.strip().casefold())
    return None


def resolve_selected_project_context(ctx: dict[str, Any]) -> dict[str, Any]:
    repository = Path(ctx["repository"]).resolve()
    session = ctx.get("session") or {}
    selected = _first_string(session, ("selected_project", "project_file"))

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "matched": False,
        "status": "NOT_APPLICABLE",
        "selected_project": selected,
        "facts": {},
        "source": None,
    }
    if not selected:
        return result

    try:
        path = _repo_path(repository, selected)
    except Exception:
        return {
            **result,
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_PATH_INVALID",
        }

    if not path.is_file() or path.suffix.lower() != ".json":
        return {
            **result,
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_BINDING_REQUIRED",
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            **result,
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_BINDING_INVALID",
            "message": str(exc),
        }
    if not isinstance(payload, dict):
        return {
            **result,
            "matched": True,
            "status": "BLOCKED",
            "reason": "SELECTED_PROJECT_BINDING_INVALID",
        }

    location = _first_string(
        payload, ("location", "project_location", "address", "site")
    )
    country_name = _first_string(payload, ("country", "country_name"))
    country_code = _country_code(payload, country_name)
    municipality = _first_string(payload, ("municipality", "gemeente"))
    postal_code = _first_string(payload, ("postal_code", "postcode", "zip_code"))

    # Optional nested context often present in Phoenix project bindings.
    for key in ("site", "project_context", "location_context"):
        nested = payload.get(key)
        if not isinstance(nested, dict):
            continue
        location = location or _first_string(
            nested, ("location", "project_location", "address")
        )
        country_name = country_name or _first_string(
            nested, ("country", "country_name")
        )
        country_code = country_code or _country_code(nested, country_name)
        municipality = municipality or _first_string(
            nested, ("municipality", "gemeente")
        )
        postal_code = postal_code or _first_string(
            nested, ("postal_code", "postcode", "zip_code")
        )

    facts: dict[str, Any] = {}
    if location:
        facts["project_location"] = location
    if country_name:
        facts["country_name"] = country_name
    if country_code:
        facts["country_code"] = country_code
    if municipality:
        facts["municipality"] = municipality
    if postal_code:
        facts["postal_code"] = postal_code

    return {
        **result,
        "matched": True,
        "status": "PASSED",
        "facts": facts,
        "source": path.as_posix(),
        "source_kind": "SELECTED_PROJECT_EXPLICIT_FACTS",
        "jurisdiction_confirmed": False,
        "automatic_legal_conclusion": False,
        "professional_review_required": True,
    }


def merge_selected_project_facts(
    project_context: dict[str, Any],
    bridge_result: dict[str, Any],
) -> dict[str, Any]:
    """Merge explicit facts without overwriting already-resolved facts."""
    if bridge_result.get("status") != "PASSED":
        return project_context
    facts = project_context.setdefault("facts", {})
    if not isinstance(facts, dict):
        facts = {}
        project_context["facts"] = facts
    for key, value in (bridge_result.get("facts") or {}).items():
        if value not in (None, "") and not facts.get(key):
            facts[key] = value
    project_context["selected_project_context"] = {
        "schema_version": bridge_result.get("schema_version"),
        "source": bridge_result.get("source"),
        "source_kind": bridge_result.get("source_kind"),
        "jurisdiction_confirmed": False,
        "automatic_legal_conclusion": False,
    }
    return project_context
