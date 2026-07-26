"""Safe source-catalog and rule-mapping registry for BB17.3."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlsplit

from .models import (
    MappingStatus,
    RightsClass,
    RuleMapping,
    RuleMappingSet,
    SourceCatalog,
    SourceRecord,
    SourceStatus,
)

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{1,159}$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_STORAGE_POLICIES = {
    "metadata_only_until_review",
    "public_snapshot_after_review",
    "external_reference_only",
}
_ALLOWED_CONFIDENCE = {"unrated", "low", "medium", "high"}


class SourceMappingRegistry:
    """Load and validate source catalogs and mapping sets."""

    def load_source_catalog(self, path: str | Path) -> SourceCatalog:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Source catalog root must be an object.")
        return self.load_source_catalog_dict(payload)

    def load_source_catalog_directory(
        self,
        directory: str | Path,
    ) -> tuple[SourceCatalog, ...]:
        catalogs = tuple(
            self.load_source_catalog(path)
            for path in sorted(Path(directory).glob("*.json"))
        )
        ids = [catalog.id for catalog in catalogs]
        jurisdictions = [catalog.jurisdiction_id for catalog in catalogs]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate source catalog identifiers.")
        if len(jurisdictions) != len(set(jurisdictions)):
            raise ValueError("Only one source catalog per jurisdiction is allowed.")
        return catalogs

    def load_source_catalog_dict(
        self,
        payload: Mapping[str, Any],
    ) -> SourceCatalog:
        catalog_id = self._required_text(payload, "id")
        jurisdiction_id = self._required_text(payload, "jurisdiction_id")
        self._validate_id(catalog_id, "catalog id")
        self._validate_id(jurisdiction_id, "jurisdiction id")

        raw_sources = payload.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise ValueError("Source catalog requires at least one source.")
        sources = tuple(
            self._load_source(item, jurisdiction_id)
            for item in raw_sources
        )
        source_ids = [source.id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError(f"{catalog_id}: duplicate source identifiers.")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Catalog metadata must be an object.")

        return SourceCatalog(
            id=catalog_id,
            jurisdiction_id=jurisdiction_id,
            version=self._required_text(payload, "version"),
            status=self._required_text(payload, "status"),
            sources=sources,
            metadata=dict(metadata),
        )

    def load_mapping_set(self, path: str | Path) -> RuleMappingSet:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Rule mapping root must be an object.")
        return self.load_mapping_set_dict(payload)

    def load_mapping_directory(
        self,
        directory: str | Path,
    ) -> tuple[RuleMappingSet, ...]:
        sets = tuple(
            self.load_mapping_set(path)
            for path in sorted(Path(directory).glob("*.json"))
        )
        ids = [item.id for item in sets]
        jurisdictions = [item.jurisdiction_id for item in sets]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate mapping-set identifiers.")
        if len(jurisdictions) != len(set(jurisdictions)):
            raise ValueError("Only one mapping set per jurisdiction is allowed.")
        return sets

    def load_mapping_set_dict(
        self,
        payload: Mapping[str, Any],
    ) -> RuleMappingSet:
        mapping_set_id = self._required_text(payload, "id")
        jurisdiction_id = self._required_text(payload, "jurisdiction_id")
        self._validate_id(mapping_set_id, "mapping-set id")
        self._validate_id(jurisdiction_id, "jurisdiction id")

        target_profile = self._required_text(payload, "target_profile")
        self._validate_relative_path(target_profile)

        required_rule_ids = self._string_tuple(payload, "required_rule_ids")
        if len(required_rule_ids) != len(set(required_rule_ids)):
            raise ValueError("required_rule_ids contains duplicates.")
        for rule_id in required_rule_ids:
            self._validate_id(rule_id, "Phoenix rule id")

        raw_mappings = payload.get("mappings", [])
        if not isinstance(raw_mappings, list):
            raise ValueError("mappings must be a list.")
        mappings = tuple(
            self._load_mapping(item, jurisdiction_id)
            for item in raw_mappings
        )
        mapping_ids = [mapping.id for mapping in mappings]
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("Duplicate mapping identifiers.")

        semantic_keys = [
            (mapping.phoenix_rule_id, mapping.source_id, mapping.locator)
            for mapping in mappings
        ]
        if len(semantic_keys) != len(set(semantic_keys)):
            raise ValueError("Duplicate semantic rule mapping.")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Mapping metadata must be an object.")

        return RuleMappingSet(
            id=mapping_set_id,
            jurisdiction_id=jurisdiction_id,
            version=self._required_text(payload, "version"),
            target_profile=target_profile,
            required_rule_ids=required_rule_ids,
            mappings=mappings,
            status=self._required_text(payload, "status"),
            metadata=dict(metadata),
        )

    def validate_pair(
        self,
        catalog: SourceCatalog,
        mapping_set: RuleMappingSet,
    ) -> None:
        if catalog.jurisdiction_id != mapping_set.jurisdiction_id:
            raise ValueError(
                "Source catalog and mapping set belong to different jurisdictions."
            )
        source_ids = {source.id for source in catalog.sources}
        unknown = sorted(
            {mapping.source_id for mapping in mapping_set.mappings} - source_ids
        )
        if unknown:
            raise ValueError(f"Mappings reference unknown source ids: {unknown}")

    def fingerprint_catalog(self, catalog: SourceCatalog) -> str:
        return self._fingerprint(catalog.to_dict())

    def fingerprint_mapping_set(self, mapping_set: RuleMappingSet) -> str:
        return self._fingerprint(mapping_set.to_dict())

    def _load_source(
        self,
        payload: Any,
        jurisdiction_id: str,
    ) -> SourceRecord:
        if not isinstance(payload, Mapping):
            raise ValueError("Every source must be an object.")
        source_id = self._required_text(payload, "id")
        self._validate_id(source_id, "source id")

        source_jurisdiction = self._required_text(payload, "jurisdiction_id")
        if source_jurisdiction != jurisdiction_id:
            raise ValueError(
                f"{source_id}: source jurisdiction differs from catalog."
            )

        canonical_uri = self._required_text(payload, "canonical_uri")
        self._validate_uri(canonical_uri)

        storage_policy = self._required_text(payload, "content_storage_policy")
        if storage_policy not in _ALLOWED_STORAGE_POLICIES:
            raise ValueError(f"{source_id}: invalid content storage policy.")

        effective_from = self._optional_text(payload, "effective_from")
        effective_until = self._optional_text(payload, "effective_until")
        if effective_from:
            start = date.fromisoformat(effective_from)
            if effective_until and date.fromisoformat(effective_until) < start:
                raise ValueError(
                    f"{source_id}: effective_until precedes effective_from."
                )
        elif effective_until:
            date.fromisoformat(effective_until)

        verified_at = self._optional_text(payload, "verified_at")
        if verified_at:
            datetime.fromisoformat(verified_at.replace("Z", "+00:00"))

        sha = self._optional_text(payload, "snapshot_sha256")
        if sha and not _SHA256.fullmatch(sha):
            raise ValueError(f"{source_id}: invalid snapshot SHA-256.")

        status = SourceStatus(self._required_text(payload, "status"))
        verified_by = self._optional_text(payload, "verified_by")
        if status == SourceStatus.VERIFIED and (not verified_at or not verified_by):
            raise ValueError(
                f"{source_id}: verified sources require verified_at and verified_by."
            )

        topics = self._string_tuple(payload, "topics")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError(f"{source_id}: metadata must be an object.")

        return SourceRecord(
            id=source_id,
            jurisdiction_id=source_jurisdiction,
            title=self._required_text(payload, "title"),
            authority=self._required_text(payload, "authority"),
            canonical_uri=canonical_uri,
            status=status,
            rights_class=RightsClass(self._required_text(payload, "rights_class")),
            content_storage_policy=storage_policy,
            required=bool(payload.get("required", True)),
            publication_id=self._optional_text(payload, "publication_id"),
            edition=self._optional_text(payload, "edition"),
            effective_from=effective_from,
            effective_until=effective_until,
            verified_at=verified_at,
            verified_by=verified_by,
            snapshot_sha256=sha,
            topics=topics,
            metadata=dict(metadata),
        )

    def _load_mapping(
        self,
        payload: Any,
        jurisdiction_id: str,
    ) -> RuleMapping:
        if not isinstance(payload, Mapping):
            raise ValueError("Every rule mapping must be an object.")
        mapping_id = self._required_text(payload, "id")
        self._validate_id(mapping_id, "mapping id")

        source_jurisdiction = self._required_text(payload, "jurisdiction_id")
        if source_jurisdiction != jurisdiction_id:
            raise ValueError(
                f"{mapping_id}: mapping jurisdiction differs from mapping set."
            )

        rule_id = self._required_text(payload, "phoenix_rule_id")
        source_id = self._required_text(payload, "source_id")
        self._validate_id(rule_id, "Phoenix rule id")
        self._validate_id(source_id, "source id")

        confidence = str(payload.get("confidence", "unrated"))
        if confidence not in _ALLOWED_CONFIDENCE:
            raise ValueError(f"{mapping_id}: invalid confidence value.")

        evidence_sha256 = self._optional_text(payload, "evidence_sha256")
        if evidence_sha256 and not _SHA256.fullmatch(evidence_sha256):
            raise ValueError(f"{mapping_id}: invalid evidence SHA-256.")

        status = MappingStatus(self._required_text(payload, "status"))
        reviewer = self._optional_text(payload, "reviewer")
        reviewed_at = self._optional_text(payload, "reviewed_at")
        if reviewed_at:
            datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if status == MappingStatus.APPROVED and (not reviewer or not reviewed_at):
            raise ValueError(
                f"{mapping_id}: approved mappings require reviewer evidence."
            )

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError(f"{mapping_id}: metadata must be an object.")

        return RuleMapping(
            id=mapping_id,
            jurisdiction_id=source_jurisdiction,
            phoenix_rule_id=rule_id,
            source_id=source_id,
            locator=self._required_text(payload, "locator"),
            status=status,
            interpretation_note=str(payload.get("interpretation_note", "")),
            confidence=confidence,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            evidence_sha256=evidence_sha256,
            metadata=dict(metadata),
        )

    @staticmethod
    def _validate_uri(value: str) -> None:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError(f"Unsupported or incomplete source URI: {value}")
        if parsed.username or parsed.password:
            raise ValueError("Source URIs may not contain credentials.")

    @staticmethod
    def _validate_relative_path(value: str) -> None:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe repository path: {value}")

    @staticmethod
    def _required_text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Required text field missing or empty: {key}")
        return value.strip()

    @staticmethod
    def _optional_text(payload: Mapping[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Optional field must be non-empty text: {key}")
        return value.strip()

    @staticmethod
    def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
        value = payload.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(f"{key} must be a list of strings.")
        return tuple(item.strip() for item in value)

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value!r}")

    @staticmethod
    def _fingerprint(payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
