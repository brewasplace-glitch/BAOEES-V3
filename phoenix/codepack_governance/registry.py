"""Versioned source registry for Phoenix codepacks."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .models import (
    ActivationState,
    CodepackManifest,
    ReviewStatus,
    SourceReference,
    SourceStatus,
)

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class CodepackRegistry:
    """Load and validate codepack governance manifests."""

    def load_file(self, path: str | Path) -> CodepackManifest:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Codepack manifest root must be an object.")
        return self.load_dict(payload)

    def load_directory(self, directory: str | Path) -> tuple[CodepackManifest, ...]:
        manifests = tuple(
            self.load_file(path)
            for path in sorted(Path(directory).glob("*.json"))
        )
        identifiers = [manifest.id for manifest in manifests]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Duplicate codepack identifiers in registry.")
        return manifests

    def load_dict(self, payload: Mapping[str, Any]) -> CodepackManifest:
        codepack_id = self._required_text(payload, "id")
        self._validate_id(codepack_id, "codepack id")
        profile_path = self._required_text(payload, "profile_path")
        self._validate_relative_path(profile_path)

        raw_sources = payload.get("sources", [])
        if not isinstance(raw_sources, list):
            raise ValueError("'sources' must be a list.")
        sources = tuple(self._load_source(item) for item in raw_sources)
        source_ids = [source.id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError(f"{codepack_id}: duplicate source identifiers.")

        raw_supersedes = payload.get("supersedes", [])
        if not isinstance(raw_supersedes, list) or not all(
            isinstance(value, str) for value in raw_supersedes
        ):
            raise ValueError("'supersedes' must be a list of identifiers.")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("'metadata' must be an object.")

        manifest = CodepackManifest(
            id=codepack_id,
            name=self._required_text(payload, "name"),
            version=self._required_text(payload, "version"),
            jurisdiction=self._required_text(payload, "jurisdiction"),
            profile_path=profile_path,
            regulatory_claim=bool(payload.get("regulatory_claim", False)),
            review_status=ReviewStatus(self._required_text(payload, "review_status")),
            activation_state=ActivationState(
                self._required_text(payload, "activation_state")
            ),
            sources=sources,
            reviewed_by=self._optional_text(payload, "reviewed_by"),
            reviewed_at=self._optional_text(payload, "reviewed_at"),
            supersedes=tuple(raw_supersedes),
            metadata=dict(metadata),
        )
        self.validate_manifest(manifest)
        return manifest

    def validate_manifest(self, manifest: CodepackManifest) -> None:
        if manifest.regulatory_claim and not manifest.sources:
            raise ValueError(
                f"{manifest.id}: regulatory codepacks require source metadata."
            )

        if manifest.activation_state == ActivationState.ACTIVE:
            if manifest.review_status != ReviewStatus.VALIDATED:
                raise ValueError(
                    f"{manifest.id}: only validated codepacks may be active."
                )
            if not manifest.reviewed_by or not manifest.reviewed_at:
                raise ValueError(
                    f"{manifest.id}: active codepacks require review evidence."
                )
            if manifest.regulatory_claim:
                for source in manifest.sources:
                    if source.source_status != SourceStatus.VERIFIED:
                        raise ValueError(
                            f"{manifest.id}: active regulatory sources must be verified."
                        )
                    if not source.effective_from:
                        raise ValueError(
                            f"{manifest.id}: active regulatory sources require effective dates."
                        )

    def fingerprint(self, manifests: tuple[CodepackManifest, ...]) -> str:
        payload = json.dumps(
            [manifest.to_dict() for manifest in sorted(manifests, key=lambda x: x.id)],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def export_index(
        self,
        manifests: tuple[CodepackManifest, ...],
        output_path: str | Path,
    ) -> Path:
        data = {
            "schema_version": "phoenix.codepack-registry/1.0",
            "fingerprint_sha256": self.fingerprint(manifests),
            "codepack_count": len(manifests),
            "active_codepacks": [
                manifest.id
                for manifest in manifests
                if manifest.activation_state == ActivationState.ACTIVE
            ],
            "codepacks": [manifest.to_dict() for manifest in manifests],
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def _load_source(self, payload: Any) -> SourceReference:
        if not isinstance(payload, Mapping):
            raise ValueError("Every source reference must be an object.")
        source_id = self._required_text(payload, "id")
        self._validate_id(source_id, "source id")

        effective_from = self._optional_text(payload, "effective_from")
        effective_until = self._optional_text(payload, "effective_until")
        start = date.fromisoformat(effective_from) if effective_from else None
        end = date.fromisoformat(effective_until) if effective_until else None
        if start and end and end < start:
            raise ValueError(
                f"{source_id}: effective_until precedes effective_from."
            )

        source_sha256 = self._optional_text(payload, "source_sha256")
        if source_sha256 and not _SHA256.fullmatch(source_sha256):
            raise ValueError(f"{source_id}: invalid SHA-256 value.")

        return SourceReference(
            id=source_id,
            title=self._required_text(payload, "title"),
            publisher=self._required_text(payload, "publisher"),
            publication_id=self._required_text(payload, "publication_id"),
            edition=self._required_text(payload, "edition"),
            source_status=SourceStatus(
                self._required_text(payload, "source_status")
            ),
            canonical_uri=self._optional_text(payload, "canonical_uri"),
            effective_from=effective_from,
            effective_until=effective_until,
            license_class=str(payload.get("license_class", "metadata-only")),
            source_sha256=source_sha256,
            rights_note=str(payload.get("rights_note", "")),
        )

    @staticmethod
    def _validate_relative_path(value: str) -> None:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe profile path: {value}")

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
    def _validate_id(value: str, label: str) -> None:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value!r}")
