"""BB17 Building Code Engine orchestration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .models import CodeProfile, ComplianceReport, RuleEvaluation, RuleResultStatus
from .safe_eval import SafeExpressionEvaluator


class BuildingCodeEngine:
    SCHEMA_VERSION = "phoenix.building-code-report/1.0"
    VERSION = "1.0.0"

    def evaluate(
        self,
        model: Mapping[str, Any] | Any,
        profile: CodeProfile,
        *,
        parameters: Mapping[str, Any] | None = None,
    ) -> ComplianceReport:
        data = self._normalise_model(model)
        model_fingerprint = self.fingerprint_model(data)
        evaluator = SafeExpressionEvaluator(data, parameters)
        evaluations: list[RuleEvaluation] = []
        for rule in profile.rules:
            evaluation_id = self._evaluation_id(
                profile.id, profile.version, rule.id, model_fingerprint
            )
            evidence = tuple(
                {"path": path, "value": self._extract_path(data, path)}
                for path in rule.evidence_paths
            )
            try:
                if rule.applies_when and not evaluator.evaluate(rule.applies_when):
                    evaluations.append(RuleEvaluation(
                        evaluation_id=evaluation_id,
                        rule_id=rule.id,
                        title=rule.title,
                        discipline=rule.discipline,
                        severity=rule.severity,
                        status=RuleResultStatus.NOT_APPLICABLE,
                        message="Rule is not applicable to this model.",
                        evidence=evidence,
                        references=rule.references,
                    ))
                    continue
                passed = evaluator.evaluate(rule.expression)
                evaluations.append(RuleEvaluation(
                    evaluation_id=evaluation_id,
                    rule_id=rule.id,
                    title=rule.title,
                    discipline=rule.discipline,
                    severity=rule.severity,
                    status=RuleResultStatus.PASS if passed else RuleResultStatus.FAIL,
                    message="Rule passed." if passed else rule.failure_message,
                    evidence=evidence,
                    references=rule.references,
                ))
            except Exception as exc:
                evaluations.append(RuleEvaluation(
                    evaluation_id=evaluation_id,
                    rule_id=rule.id,
                    title=rule.title,
                    discipline=rule.discipline,
                    severity=rule.severity,
                    status=RuleResultStatus.ERROR,
                    message="Rule evaluation could not be completed.",
                    evidence=evidence,
                    references=rule.references,
                    error=f"{type(exc).__name__}: {exc}",
                ))
        return ComplianceReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            profile_id=profile.id,
            profile_version=profile.version,
            jurisdiction=profile.jurisdiction,
            profile_status=profile.status,
            model_fingerprint_sha256=model_fingerprint,
            evaluations=evaluations,
            metadata={
                "parameters": dict(parameters or {}),
                "rule_count": len(profile.rules),
                "non_certifying_engine": True,
            },
        )

    def export_report(self, report: ComplianceReport, profile: CodeProfile, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = report.to_dict(profile.fail_severities)
        data["report_fingerprint_sha256"] = self.fingerprint_report(report, profile)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def fingerprint_model(model: Mapping[str, Any]) -> str:
        raw = json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def fingerprint_report(report: ComplianceReport, profile: CodeProfile) -> str:
        raw = json.dumps(
            report.to_dict(profile.fail_severities),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _normalise_model(model: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(model, Mapping):
            return dict(model)
        converter = getattr(model, "to_dict", None)
        if callable(converter):
            data = converter()
            if not isinstance(data, Mapping):
                raise TypeError("model.to_dict() must return a mapping.")
            return dict(data)
        raise TypeError("model must be a mapping or expose to_dict().")

    @staticmethod
    def _extract_path(model: Mapping[str, Any], path: str) -> Any:
        current: Any = model
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        return current

    @staticmethod
    def _evaluation_id(profile_id: str, profile_version: str, rule_id: str, model_fingerprint: str) -> str:
        raw = f"{profile_id}|{profile_version}|{rule_id}|{model_fingerprint}".encode("utf-8")
        return "BCE-EVAL-" + hashlib.sha256(raw).hexdigest()[:20].upper()
