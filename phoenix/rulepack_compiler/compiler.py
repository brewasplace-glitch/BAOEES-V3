"""Jurisdiction rulepack compiler and release gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import (
    CompilationIssue,
    CompilationResult,
    CompilationStatus,
    RuleDefinitionSet,
)


class JurisdictionRulepackCompiler:
    SCHEMA_VERSION = "phoenix.rulepack-compilation/1.0"
    VERSION = "1.0.0"

    def compile(self, catalog: Any, mapping_set: Any, definitions: RuleDefinitionSet) -> CompilationResult:
        issues: list[CompilationIssue] = []

        jurisdictions = {
            str(catalog.jurisdiction_id),
            str(mapping_set.jurisdiction_id),
            str(definitions.jurisdiction_id),
        }
        if len(jurisdictions) != 1:
            issues.append(
                CompilationIssue(
                    "RPC-JURISDICTION-001",
                    "critical",
                    "Catalog, mapping set and definitions belong to different jurisdictions.",
                )
            )

        source_by_id = {source.id: source for source in catalog.sources}
        definition_by_id = {rule.id: rule for rule in definitions.rules}
        approved_mapping_by_rule: dict[str, Any] = {}

        if getattr(catalog, "status", "") not in {"reviewed", "validated"}:
            issues.append(
                CompilationIssue(
                    "RPC-CATALOG-001",
                    "error",
                    "Source catalog is not reviewed or validated.",
                    getattr(catalog, "id", None),
                )
            )
        if getattr(mapping_set, "status", "") != "validated":
            issues.append(
                CompilationIssue(
                    "RPC-MAPPING-001",
                    "error",
                    "Rule mapping set is not validated.",
                    getattr(mapping_set, "id", None),
                )
            )
        if definitions.status != "validated":
            issues.append(
                CompilationIssue(
                    "RPC-DEFINITION-001",
                    "error",
                    "Rule definition set is not validated.",
                    definitions.id,
                )
            )

        for source in catalog.sources:
            if source.required and str(source.status.value) != "verified":
                issues.append(
                    CompilationIssue(
                        "RPC-SOURCE-001",
                        "error",
                        "Required source is not verified.",
                        source.id,
                    )
                )

        for mapping in mapping_set.mappings:
            if str(mapping.status.value) != "approved":
                continue
            if mapping.phoenix_rule_id in approved_mapping_by_rule:
                issues.append(
                    CompilationIssue(
                        "RPC-MAPPING-002",
                        "error",
                        "More than one approved mapping exists for one Phoenix rule.",
                        mapping.phoenix_rule_id,
                    )
                )
            approved_mapping_by_rule[mapping.phoenix_rule_id] = mapping

        required_rule_ids = tuple(mapping_set.required_rule_ids)
        for rule_id in required_rule_ids:
            if rule_id not in approved_mapping_by_rule:
                issues.append(
                    CompilationIssue(
                        "RPC-MAPPING-003",
                        "error",
                        "Required rule has no approved source mapping.",
                        rule_id,
                    )
                )
            if rule_id not in definition_by_id:
                issues.append(
                    CompilationIssue(
                        "RPC-DEFINITION-002",
                        "error",
                        "Required rule has no executable definition.",
                        rule_id,
                    )
                )

        for rule_id, mapping in approved_mapping_by_rule.items():
            if mapping.source_id not in source_by_id:
                issues.append(
                    CompilationIssue(
                        "RPC-SOURCE-002",
                        "critical",
                        "Approved mapping references an unknown source.",
                        mapping.id,
                    )
                )
            if rule_id not in definition_by_id:
                issues.append(
                    CompilationIssue(
                        "RPC-DEFINITION-003",
                        "error",
                        "Approved mapping has no executable rule definition.",
                        rule_id,
                    )
                )

        blocked = any(issue.severity in {"error", "critical"} for issue in issues)
        profile: dict[str, Any] | None = None
        if not blocked:
            compiled_rules: list[dict[str, Any]] = []
            for rule_id in sorted(approved_mapping_by_rule):
                mapping = approved_mapping_by_rule[rule_id]
                definition = definition_by_id[rule_id]
                source = source_by_id[mapping.source_id]
                compiled_rules.append(
                    {
                        "id": definition.id,
                        "title": definition.title,
                        "description": definition.description,
                        "discipline": definition.discipline,
                        "severity": definition.severity,
                        "expression": definition.expression,
                        "failure_message": definition.failure_message,
                        "applies_when": definition.applies_when,
                        "evidence_paths": list(definition.evidence_paths),
                        "references": [
                            {
                                "type": "jurisdiction_source",
                                "source_id": source.id,
                                "title": source.title,
                                "authority": source.authority,
                                "publication_id": source.publication_id,
                                "edition": source.edition,
                                "canonical_uri": source.canonical_uri,
                                "locator": mapping.locator,
                                "mapping_id": mapping.id,
                                "mapping_evidence_sha256": mapping.evidence_sha256,
                            }
                        ],
                        "metadata": {
                            **definition.metadata,
                            "mapping_confidence": mapping.confidence,
                            "interpretation_note": mapping.interpretation_note,
                            "reviewer": mapping.reviewer,
                            "reviewed_at": mapping.reviewed_at,
                        },
                    }
                )

            profile = {
                "id": f"PHX-COMPILED-{definitions.jurisdiction_id}-{definitions.version}",
                "name": f"Compiled {definitions.jurisdiction_id} Building Codepack",
                "version": definitions.version,
                "jurisdiction": definitions.jurisdiction_id,
                "status": "compiled-pending-release-review",
                "fail_severities": ["error", "critical"],
                "metadata": {
                    "compiler_version": self.VERSION,
                    "source_catalog_id": catalog.id,
                    "source_catalog_version": catalog.version,
                    "mapping_set_id": mapping_set.id,
                    "mapping_set_version": mapping_set.version,
                    "definition_set_id": definitions.id,
                    "definition_set_version": definitions.version,
                    "regulatory_activation_allowed": False,
                    "release_review_required": True,
                },
                "rules": compiled_rules,
            }

        result = CompilationResult(
            schema_version=self.SCHEMA_VERSION,
            compiler_version=self.VERSION,
            jurisdiction_id=str(catalog.jurisdiction_id),
            status=CompilationStatus.BLOCKED if blocked else CompilationStatus.COMPILED,
            source_catalog_id=str(catalog.id),
            mapping_set_id=str(mapping_set.id),
            definition_set_id=definitions.id,
            profile=profile,
            issues=issues,
            metadata={
                "required_rule_count": len(required_rule_ids),
                "approved_mapping_count": len(approved_mapping_by_rule),
                "definition_count": len(definitions.rules),
            },
        )
        result.metadata["fingerprint_sha256"] = self.fingerprint(result)
        return result

    def export_result(self, result: CompilationResult, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def export_profile(self, result: CompilationResult, output_path: str | Path) -> Path:
        if not result.compiled or result.profile is None:
            raise ValueError("Blocked compilation results cannot be exported as code profiles.")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result.profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def fingerprint(result: CompilationResult) -> str:
        payload = result.to_dict()
        payload.get("metadata", {}).pop("fingerprint_sha256", None)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
