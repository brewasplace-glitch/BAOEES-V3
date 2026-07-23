"""Permit & Compliance Engine for Project Phoenix — Wave 15.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


ENGINE_ID = "phoenix.permit_compliance.wave15_8"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"


class PermitComplianceError(RuntimeError):
    """Raised when permit/compliance validation cannot be completed."""


@dataclass(frozen=True)
class PermitProjectContext:
    project_id: str
    jurisdiction: str
    permit_type: str
    digital_twin_revision: int
    human_approval_required: bool = True

    def validate(self) -> None:
        if not self.project_id.strip():
            raise PermitComplianceError("project_id must not be empty.")
        if not self.jurisdiction.strip():
            raise PermitComplianceError("jurisdiction must not be empty.")
        if not self.permit_type.strip():
            raise PermitComplianceError("permit_type must not be empty.")
        if self.digital_twin_revision < 0:
            raise PermitComplianceError("digital_twin_revision must be zero or positive.")


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    title: str
    path: str
    operator: str
    expected: Any = None
    severity: str = "error"
    required: bool = True
    standard_reference: str = ""
    remediation: str = ""

    def validate(self) -> None:
        if not self.rule_id.strip():
            raise PermitComplianceError("rule_id must not be empty.")
        if not self.title.strip():
            raise PermitComplianceError("title must not be empty.")
        if not self.path.strip():
            raise PermitComplianceError("path must not be empty.")
        if self.operator not in {
            "exists", "equals", "not_equals", "gte", "lte", "in", "not_empty"
        }:
            raise PermitComplianceError(f"Unsupported operator: {self.operator}")
        if self.severity not in {"info", "warning", "error", "critical"}:
            raise PermitComplianceError(f"Unsupported severity: {self.severity}")


@dataclass(frozen=True)
class ComplianceFinding:
    rule_id: str
    title: str
    status: str
    severity: str
    path: str
    actual: Any
    expected: Any
    standard_reference: str
    remediation: str


class PermitComplianceEngine:
    """Evaluates Digital Twin data against versioned permit/compliance rules."""

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _resolve_path(data: Mapping[str, Any], path: str) -> tuple[bool, Any]:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return False, None
        return True, current

    @staticmethod
    def _evaluate(operator: str, exists: bool, actual: Any, expected: Any) -> bool:
        if operator == "exists":
            return exists
        if operator == "not_empty":
            return exists and actual not in (None, "", [], {}, ())
        if not exists:
            return False
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "gte":
            try:
                return actual >= expected
            except TypeError:
                return False
        if operator == "lte":
            try:
                return actual <= expected
            except TypeError:
                return False
        if operator == "in":
            try:
                return actual in expected
            except TypeError:
                return False
        raise PermitComplianceError(f"Unsupported operator: {operator}")

    def evaluate(
        self,
        *,
        context: PermitProjectContext,
        digital_twin: Mapping[str, Any],
        rules: Iterable[ComplianceRule],
        rule_set_id: str,
        rule_set_version: str,
    ) -> dict[str, Any]:
        context.validate()
        if not rule_set_id.strip() or not rule_set_version.strip():
            raise PermitComplianceError("rule_set_id and rule_set_version are required.")

        findings: list[ComplianceFinding] = []
        seen: set[str] = set()

        for rule in rules:
            rule.validate()
            if rule.rule_id in seen:
                raise PermitComplianceError(f"Duplicate rule_id: {rule.rule_id}")
            seen.add(rule.rule_id)

            exists, actual = self._resolve_path(digital_twin, rule.path)
            passed = self._evaluate(rule.operator, exists, actual, rule.expected)
            findings.append(
                ComplianceFinding(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    status="passed" if passed else "failed",
                    severity=rule.severity,
                    path=rule.path,
                    actual=actual,
                    expected=rule.expected,
                    standard_reference=rule.standard_reference,
                    remediation=rule.remediation,
                )
            )

        failed = [f for f in findings if f.status == "failed"]
        blocking = [f for f in failed if f.severity in {"error", "critical"}]
        warnings = [f for f in failed if f.severity == "warning"]

        completeness = {
            "total_rules": len(findings),
            "passed_rules": len(findings) - len(failed),
            "failed_rules": len(failed),
            "blocking_findings": len(blocking),
            "warnings": len(warnings),
        }
        completeness["score_percent"] = (
            100.0 if not findings else round(100 * completeness["passed_rules"] / len(findings), 2)
        )

        if blocking:
            permit_status = "blocked"
        elif failed or context.human_approval_required:
            permit_status = "review_required"
        else:
            permit_status = "ready_for_submission"

        dossier = {
            "project_id": context.project_id,
            "jurisdiction": context.jurisdiction,
            "permit_type": context.permit_type,
            "digital_twin_revision": context.digital_twin_revision,
            "rule_set_id": rule_set_id,
            "rule_set_version": rule_set_version,
            "permit_status": permit_status,
            "required_actions": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "remediation": f.remediation,
                }
                for f in failed
            ],
        }

        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
            "context": asdict(context),
            "rule_set": {"id": rule_set_id, "version": rule_set_version},
            "permit_status": permit_status,
            "completeness": completeness,
            "findings": [asdict(f) for f in findings],
            "permit_dossier": dossier,
            "integration_contract": {
                "upstream_engine": "phoenix.digital_twin_synchronization.wave15_7",
                "orchestrator": "phoenix.autonomous_design_orchestrator.wave15_6",
                "target_core": "phoenix.core.v2_0",
            },
            "limitations": [
                "Rules are only as complete and current as the configured rule set.",
                "This engine does not replace authority review or professional certification.",
                "External legal and standards updates require controlled rule-set updates.",
                "Human approval is enabled by default.",
            ],
        }
        result["evidence"] = {
            "algorithm": "sha256",
            "digital_twin_sha256": self._digest(digital_twin),
            "rules_sha256": self._digest([asdict(rule) for rule in rules]),
            "result_sha256": self._digest(result),
        }
        return result

    def write_result(
        self,
        *,
        context: PermitProjectContext,
        digital_twin: Mapping[str, Any],
        rules: Iterable[ComplianceRule],
        rule_set_id: str,
        rule_set_version: str,
        destination: str | Path,
    ) -> Path:
        result = self.evaluate(
            context=context,
            digital_twin=digital_twin,
            rules=tuple(rules),
            rule_set_id=rule_set_id,
            rule_set_version=rule_set_version,
        )
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(path)
        return path
