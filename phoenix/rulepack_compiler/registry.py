"""Rule-definition registry for BB17.4."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .models import RuleDefinition, RuleDefinitionSet
from .safety import validate_expression

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{1,159}$")
_ALLOWED_SEVERITIES = {"info", "warning", "error", "critical"}


class RuleDefinitionRegistry:
    def load_file(self, path: str | Path) -> RuleDefinitionSet:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Rule-definition root must be an object.")
        return self.load_dict(payload)

    def load_dict(self, payload: Mapping[str, Any]) -> RuleDefinitionSet:
        set_id = self._text(payload, "id")
        jurisdiction = self._text(payload, "jurisdiction_id")
        self._validate_id(set_id, "definition-set id")
        self._validate_id(jurisdiction, "jurisdiction id")

        raw_rules = payload.get("rules", [])
        if not isinstance(raw_rules, list):
            raise ValueError("rules must be a list.")
        rules = tuple(self._load_rule(item) for item in raw_rules)
        ids = [item.id for item in rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate rule-definition identifiers.")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be an object.")

        return RuleDefinitionSet(
            id=set_id,
            jurisdiction_id=jurisdiction,
            version=self._text(payload, "version"),
            status=self._text(payload, "status"),
            rules=rules,
            metadata=dict(metadata),
        )

    def _load_rule(self, payload: Any) -> RuleDefinition:
        if not isinstance(payload, Mapping):
            raise ValueError("Every rule definition must be an object.")
        rule_id = self._text(payload, "id")
        self._validate_id(rule_id, "rule id")
        severity = self._text(payload, "severity")
        if severity not in _ALLOWED_SEVERITIES:
            raise ValueError(f"{rule_id}: unsupported severity {severity!r}.")
        expression = self._text(payload, "expression")
        validate_expression(expression)
        applies_when = payload.get("applies_when")
        if applies_when is not None:
            if not isinstance(applies_when, str) or not applies_when.strip():
                raise ValueError(f"{rule_id}: applies_when must be non-empty text.")
            validate_expression(applies_when)
        evidence_paths = payload.get("evidence_paths", [])
        if not isinstance(evidence_paths, list) or not all(
            isinstance(item, str) and item for item in evidence_paths
        ):
            raise ValueError(f"{rule_id}: evidence_paths must be strings.")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError(f"{rule_id}: metadata must be an object.")
        return RuleDefinition(
            id=rule_id,
            title=self._text(payload, "title"),
            description=self._text(payload, "description"),
            discipline=self._text(payload, "discipline"),
            severity=severity,
            expression=expression,
            failure_message=self._text(payload, "failure_message"),
            applies_when=applies_when.strip() if isinstance(applies_when, str) else None,
            evidence_paths=tuple(evidence_paths),
            metadata=dict(metadata),
        )

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Required text field missing or empty: {key}")
        return value.strip()

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value!r}")
