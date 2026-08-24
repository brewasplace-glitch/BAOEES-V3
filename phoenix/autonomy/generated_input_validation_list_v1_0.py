"""Project Phoenix C05 - Generated Input Validation List.

This module is intentionally narrow. It does not replace AAIE, evidence intake,
DOCX generation/intake, review merge, canonical JSON, or professional review
gates. It converts already-generated Phoenix input records into one deterministic
human-validation list with provenance and confidence preserved.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "phoenix.generated-input-validation-list/1.0"

CLASSIFICATIONS = {
    "AUTO_DERIVED",
    "SOURCE_BACKED_CANDIDATE",
    "ASSUMED_CANDIDATE",
    "HUMAN_REQUIRED",
    "PROFESSIONAL_REVIEW_REQUIRED",
}

_CONTAINER_KEYS = (
    "generated_inputs",
    "assumptions",
    "inputs",
    "parameters",
    "candidate_inputs",
    "validation_inputs",
)


class ValidationListError(ValueError):
    """Raised when generated-input records cannot be normalized safely."""


def available_schema_backend() -> str:
    """Report the preferred optional open-source validation backend.

    No new dependency is required for C05. Pydantic is preferred when already
    available, python-jsonschema is the fallback, and stdlib remains a safe
    deterministic last resort for list construction.
    """
    if find_spec("pydantic") is not None:
        return "pydantic"
    if find_spec("jsonschema") is not None:
        return "jsonschema"
    return "stdlib"


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


def _truthy(record: Mapping[str, Any], *keys: str) -> bool:
    for key in keys:
        value = record.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().upper() in {
            "TRUE", "YES", "Y", "1", "REQUIRED", "HUMAN_REQUIRED",
            "PROFESSIONAL_REVIEW_REQUIRED",
        }:
            return True
    return False


def _text(record: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def infer_classification(record: Mapping[str, Any]) -> str:
    explicit = _text(record, "classification", "input_classification")
    if explicit:
        explicit = explicit.upper()
        if explicit not in CLASSIFICATIONS:
            raise ValidationListError(
                f"unsupported explicit classification: {explicit}"
            )
        return explicit

    if _truthy(
        record,
        "professional_review_required",
        "professional_validation_required",
    ):
        return "PROFESSIONAL_REVIEW_REQUIRED"

    if _truthy(record, "human_required", "human_validation_required"):
        return "HUMAN_REQUIRED"

    origin = (_text(record, "origin", "provenance_type", "source_type") or "").upper()
    if "PROFESSIONAL" in origin:
        return "PROFESSIONAL_REVIEW_REQUIRED"
    if "HUMAN" in origin:
        return "HUMAN_REQUIRED"
    if "ASSUM" in origin:
        return "ASSUMED_CANDIDATE"

    if _truthy(record, "derived", "calculated", "auto_derived"):
        return "AUTO_DERIVED"

    source = _text(
        record,
        "source",
        "source_record_id",
        "source_reference",
        "evidence_reference",
    )
    if source:
        return "SOURCE_BACKED_CANDIDATE"

    if _truthy(record, "assumed", "inferred"):
        return "ASSUMED_CANDIDATE"

    # An automatically generated value with no explicit derivation or source is
    # an assumption candidate, never silently treated as verified.
    return "ASSUMED_CANDIDATE"


def _looks_like_record(value: Mapping[str, Any]) -> bool:
    field_keys = {
        "field", "name", "key", "json_path", "path",
        "value", "proposed_value", "generated_value",
    }
    return bool(field_keys.intersection(value.keys()))


def normalize_input_records(payload: Any) -> list[dict[str, Any]]:
    """Normalize common Phoenix generated-input containers to record dicts."""
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        records = []
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                raise ValidationListError(
                    f"input record at index {index} is not an object"
                )
            records.append(dict(item))
        return records

    if not isinstance(payload, Mapping):
        raise ValidationListError("payload must be an object or array")

    if _looks_like_record(payload):
        return [dict(payload)]

    records: list[dict[str, Any]] = []
    for key in _CONTAINER_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, item in enumerate(value):
                if not isinstance(item, Mapping):
                    raise ValidationListError(
                        f"{key}[{index}] is not an object"
                    )
                row = dict(item)
                row.setdefault("_container", key)
                row.setdefault("_container_index", index)
                records.append(row)

    if not records:
        raise ValidationListError(
            "no generated-input records found in supported containers"
        )
    return records


def _field_name(record: Mapping[str, Any], index: int) -> str:
    return (
        _text(record, "field", "name", "key")
        or f"generated_input_{index + 1}"
    )


def _json_path(record: Mapping[str, Any], field: str, index: int) -> str:
    explicit = _text(record, "json_path", "path")
    if explicit:
        return explicit
    container = _text(record, "_container")
    container_index = record.get("_container_index")
    if container is not None and container_index is not None:
        return f"$.{container}[{container_index}].{field}"
    return f"$.generated_inputs[{index}].{field}"


def _field_id(project_id: str | None, package_id: str | None, json_path: str) -> str:
    seed = "|".join((project_id or "", package_id or "", json_path))
    digest = sha256(seed.encode("utf-8")).hexdigest()[:12].upper()
    return f"PHX-VAL-{digest}"


def _record_value(record: Mapping[str, Any]) -> Any:
    for key in ("proposed_value", "generated_value", "value"):
        if key in record:
            return _json_safe(record[key])
    return None


def build_validation_list(
    payload: Any,
    *,
    project_id: str | None = None,
    package_id: str | None = None,
) -> dict[str, Any]:
    records = normalize_input_records(payload)
    items: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        field = _field_name(record, index)
        json_path = _json_path(record, field, index)
        classification = infer_classification(record)

        item = {
            "phoenix_field_id": _field_id(project_id, package_id, json_path),
            "field": field,
            "json_path": json_path,
            "phoenix_value": _record_value(record),
            "classification": classification,
            "source": _text(
                record,
                "source",
                "source_record_id",
                "source_reference",
                "evidence_reference",
            ),
            "confidence": _text(
                record,
                "confidence",
                "confidence_score",
                "reliability",
            ),
            "rationale": _text(
                record,
                "reason",
                "rationale",
                "note",
                "description",
            ),
            "affected_outputs": _json_safe(record.get("affected_outputs", [])),
            "review": {
                "status": "AWAITING_VALIDATION",
                "requested_action": "VALIDATE_OR_CORRECT",
                "allowed_actions": [
                    "CONFIRM",
                    "MODIFY",
                    "NOT_APPLICABLE",
                    "DEFER",
                ],
                "reviewer_action": None,
                "reviewer_value": None,
                "reviewer_comment": None,
            },
        }
        items.append(item)

    counts = Counter(item["classification"] for item in items)
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "package_id": package_id,
        "schema_validation_backend": available_schema_backend(),
        "status": "CONCEPT_INPUT_VALIDATION_REQUIRED",
        "summary": {
            "total_items": len(items),
            "classification_counts": {
                name: counts.get(name, 0)
                for name in sorted(CLASSIFICATIONS)
            },
            "awaiting_validation": len(items),
        },
        "items": items,
        "safety": {
            "concept_only_until_review": True,
            "professional_review_fabricated": False,
            "automatic_approval": False,
            "production_release": "LOCKED",
        },
    }


def write_validation_list(
    output_path: str | Path,
    payload: Any,
    *,
    project_id: str | None = None,
    package_id: str | None = None,
) -> dict[str, Any]:
    result = build_validation_list(
        payload,
        project_id=project_id,
        package_id=package_id,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
