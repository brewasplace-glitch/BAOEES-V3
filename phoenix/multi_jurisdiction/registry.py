"""Source-controlled registry for legal jurisdictions and engineering overlays."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .models import JurisdictionDefinition

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{1,127}$")


def normalise_alias(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(character for character in ascii_value.upper() if character.isalnum())


class JurisdictionRegistry:
    def load_file(self, path: str | Path) -> JurisdictionDefinition:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Jurisdiction definition root must be an object.")
        return self.load_dict(payload)

    def load_directory(self, directory: str | Path) -> tuple[JurisdictionDefinition, ...]:
        definitions = tuple(
            self.load_file(path)
            for path in sorted(Path(directory).glob("*.json"))
            if path.name != "engineering_overlays_v1_0.json"
        )
        self.validate_collection(definitions)
        return definitions

    def load_dict(self, payload: Mapping[str, Any]) -> JurisdictionDefinition:
        identifier = self._text(payload, "id")
        if not _SAFE_ID.fullmatch(identifier):
            raise ValueError(f"Invalid jurisdiction id: {identifier}")

        country_codes = self._string_tuple(payload, "country_codes")
        aliases = self._string_tuple(payload, "aliases")
        default_overlays = self._string_tuple(payload, "default_overlays")
        source_watch = self._string_tuple(payload, "source_watch")

        raw_islands = payload.get("island_overlays", {})
        if not isinstance(raw_islands, Mapping):
            raise ValueError("island_overlays must be an object.")
        island_overlays: dict[str, tuple[str, ...]] = {}
        for key, values in raw_islands.items():
            if not isinstance(key, str) or not isinstance(values, list) or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                raise ValueError("Invalid island overlay mapping.")
            island_overlays[normalise_alias(key)] = tuple(values)

        legal_manifest = self._text(payload, "legal_codepack_manifest")
        foundation_profile = self._text(payload, "foundation_profile")
        self._safe_path(legal_manifest)
        self._safe_path(foundation_profile)

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be an object.")

        mixing_policy = self._text(payload, "mixing_policy")
        if mixing_policy != "exclusive_primary":
            raise ValueError("BB17.2 requires exclusive_primary mixing policy.")

        return JurisdictionDefinition(
            id=identifier,
            name=self._text(payload, "name"),
            legal_scope=self._text(payload, "legal_scope"),
            country_codes=tuple(code.upper() for code in country_codes),
            aliases=aliases,
            legal_codepack_manifest=legal_manifest,
            foundation_profile=foundation_profile,
            default_overlays=default_overlays,
            island_overlays=island_overlays,
            source_watch=source_watch,
            mixing_policy=mixing_policy,
            metadata=dict(metadata),
        )

    def validate_collection(
        self,
        definitions: tuple[JurisdictionDefinition, ...],
    ) -> None:
        ids = [definition.id for definition in definitions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate jurisdiction identifiers.")

        alias_owner: dict[str, str] = {}
        for definition in definitions:
            candidates = (definition.id, *definition.country_codes, *definition.aliases)
            for candidate in candidates:
                alias = normalise_alias(candidate)
                if not alias:
                    raise ValueError(f"Empty jurisdiction alias in {definition.id}.")
                owner = alias_owner.get(alias)
                if owner and owner != definition.id:
                    # NL is intentionally shared with European Netherlands only;
                    # BES uses BQ and island aliases instead.
                    raise ValueError(
                        f"Alias {candidate!r} is shared by {owner} and {definition.id}."
                    )
                alias_owner[alias] = definition.id

    def load_overlays(self, path: str | Path) -> dict[str, dict[str, Any]]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or not isinstance(payload.get("overlays"), list):
            raise ValueError("Overlay registry must contain an overlays list.")
        result: dict[str, dict[str, Any]] = {}
        for raw in payload["overlays"]:
            if not isinstance(raw, Mapping):
                raise ValueError("Every overlay must be an object.")
            identifier = self._text(raw, "id")
            if identifier in result:
                raise ValueError(f"Duplicate overlay id: {identifier}")
            if not _SAFE_ID.fullmatch(identifier):
                raise ValueError(f"Invalid overlay id: {identifier}")
            result[identifier] = dict(raw)
        return result

    def fingerprint(self, definitions: tuple[JurisdictionDefinition, ...]) -> str:
        payload = json.dumps(
            [item.to_dict() for item in sorted(definitions, key=lambda item: item.id)],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or empty text field: {key}")
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
    def _safe_path(value: str) -> None:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe repository path: {value}")
