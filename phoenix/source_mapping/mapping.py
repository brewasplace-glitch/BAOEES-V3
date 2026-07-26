"""Rule mapping, coverage and activation gates for BB17.3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import (
    ActivationAssessment,
    MappingStatus,
    RuleMappingSet,
    SourceCatalog,
    SourceStatus,
)
from .registry import SourceMappingRegistry


class RuleMappingEngine:
    VERSION = "1.0.0"

    def assess_activation(
        self,
        catalog: SourceCatalog,
        mapping_set: RuleMappingSet,
    ) -> ActivationAssessment:
        SourceMappingRegistry().validate_pair(catalog, mapping_set)
        reasons: list[str] = []

        required_sources = [source for source in catalog.sources if source.required]
        verified_required = [
            source
            for source in required_sources
            if source.status == SourceStatus.VERIFIED
        ]
        if len(verified_required) != len(required_sources):
            missing = sorted(
                source.id
                for source in required_sources
                if source.status != SourceStatus.VERIFIED
            )
            reasons.append(
                "Required sources are not verified: " + ", ".join(missing)
            )

        approved_mappings = [
            mapping
            for mapping in mapping_set.mappings
            if mapping.status == MappingStatus.APPROVED
        ]
        mapped_rule_ids = {mapping.phoenix_rule_id for mapping in approved_mappings}
        missing_rule_ids = sorted(
            set(mapping_set.required_rule_ids) - mapped_rule_ids
        )
        if missing_rule_ids:
            reasons.append(
                "Required Phoenix rules have no approved source mapping: "
                + ", ".join(missing_rule_ids)
            )

        rejected = sorted(
            mapping.id
            for mapping in mapping_set.mappings
            if mapping.status == MappingStatus.REJECTED
        )
        if rejected:
            reasons.append("Rejected mappings remain in the set: " + ", ".join(rejected))

        if catalog.status not in {"reviewed", "validated"}:
            reasons.append("Source catalog status is not reviewed or validated.")
        if mapping_set.status != "validated":
            reasons.append("Rule mapping set status is not validated.")

        source_coverage = {
            "total": len(catalog.sources),
            "required": len(required_sources),
            "verified_required": len(verified_required),
        }
        mapping_coverage = {
            "total": len(mapping_set.mappings),
            "approved": len(approved_mappings),
            "required_rules": len(mapping_set.required_rule_ids),
            "approved_required_rules": len(
                set(mapping_set.required_rule_ids) & mapped_rule_ids
            ),
        }

        fingerprint = self._assessment_fingerprint(
            catalog,
            mapping_set,
            source_coverage,
            mapping_coverage,
            reasons,
        )
        return ActivationAssessment(
            jurisdiction_id=catalog.jurisdiction_id,
            eligible=not reasons,
            reasons=tuple(reasons),
            source_coverage=source_coverage,
            mapping_coverage=mapping_coverage,
            fingerprint_sha256=fingerprint,
        )

    def export_assessment(
        self,
        assessment: ActivationAssessment,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                assessment.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _assessment_fingerprint(
        catalog: SourceCatalog,
        mapping_set: RuleMappingSet,
        source_coverage: dict[str, int],
        mapping_coverage: dict[str, int],
        reasons: list[str],
    ) -> str:
        payload = {
            "catalog": catalog.to_dict(),
            "mapping_set": mapping_set.to_dict(),
            "source_coverage": source_coverage,
            "mapping_coverage": mapping_coverage,
            "reasons": reasons,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
