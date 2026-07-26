"""Source-controlled code profile loading for BB17."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .models import CodeProfile, CodeRule, RuleSeverity
from .safe_eval import SafeExpressionEvaluator

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")


class CodeProfileRegistry:
    def load_file(self, path: str | Path) -> CodeProfile:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("Code profile root must be an object.")
        return self.load_dict(data)

    def load_dict(self, data: Mapping[str, Any]) -> CodeProfile:
        profile_id = self._text(data, "id")
        self._id(profile_id, "profile id")
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError("Code profile rules must be a list.")
        rules: list[CodeRule] = []
        seen: set[str] = set()
        for raw in raw_rules:
            if not isinstance(raw, Mapping):
                raise ValueError("Every rule must be an object.")
            rule = self._rule(raw)
            if rule.id in seen:
                raise ValueError(f"Duplicate code rule id: {rule.id}")
            seen.add(rule.id)
            rules.append(rule)
        raw_fail = data.get("fail_severities", ["error", "critical"])
        if not isinstance(raw_fail, list):
            raise ValueError("fail_severities must be a list.")
        metadata = data.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Profile metadata must be an object.")
        return CodeProfile(
            id=profile_id,
            name=self._text(data, "name"),
            version=self._text(data, "version"),
            jurisdiction=self._text(data, "jurisdiction"),
            status=self._text(data, "status"),
            rules=tuple(rules),
            fail_severities=tuple(RuleSeverity(str(item)) for item in raw_fail),
            metadata=dict(metadata),
        )

    def _rule(self, data: Mapping[str, Any]) -> CodeRule:
        rule_id = self._text(data, "id")
        self._id(rule_id, "rule id")
        expression = self._text(data, "expression")
        SafeExpressionEvaluator({}).evaluate(expression)
        applies_when = data.get("applies_when")
        if applies_when is not None:
            if not isinstance(applies_when, str) or not applies_when.strip():
                raise ValueError(f"Rule {rule_id}: applies_when must be text.")
            SafeExpressionEvaluator({}).evaluate(applies_when)
        evidence = data.get("evidence_paths", [])
        references = data.get("references", [])
        metadata = data.get("metadata", {})
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise ValueError(f"Rule {rule_id}: evidence_paths must contain strings.")
        if not isinstance(references, list) or not all(isinstance(item, Mapping) for item in references):
            raise ValueError(f"Rule {rule_id}: references must contain objects.")
        if not isinstance(metadata, Mapping):
            raise ValueError(f"Rule {rule_id}: metadata must be an object.")
        return CodeRule(
            id=rule_id,
            title=self._text(data, "title"),
            description=self._text(data, "description"),
            discipline=self._text(data, "discipline"),
            severity=RuleSeverity(self._text(data, "severity")),
            expression=expression,
            failure_message=self._text(data, "failure_message"),
            applies_when=applies_when.strip() if isinstance(applies_when, str) else None,
            evidence_paths=tuple(evidence),
            references=tuple(dict(item) for item in references),
            metadata=dict(metadata),
        )

    @staticmethod
    def _text(data: Mapping[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or empty text field: {key}")
        return value.strip()

    @staticmethod
    def _id(value: str, label: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value!r}")
