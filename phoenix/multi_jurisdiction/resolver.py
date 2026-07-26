"""Deterministic legal-jurisdiction and engineering-overlay selection."""

from __future__ import annotations

from .models import (
    JurisdictionDefinition,
    JurisdictionSelection,
    LocationContext,
)
from .registry import normalise_alias


class JurisdictionResolver:
    def __init__(self, definitions: tuple[JurisdictionDefinition, ...]) -> None:
        self.definitions = definitions
        self.by_id = {item.id: item for item in definitions}
        self.aliases: dict[str, JurisdictionDefinition] = {}
        for definition in definitions:
            for value in (definition.id, *definition.country_codes, *definition.aliases):
                self.aliases[normalise_alias(value)] = definition

    def resolve(self, context: LocationContext) -> JurisdictionSelection:
        reasons: list[str] = []
        explicit = context.territory_code
        island_key = normalise_alias(context.island or "")

        if explicit:
            definition = self._lookup(explicit)
            reasons.append("Resolved from explicit territory code.")
        elif island_key in {"BONAIRE", "SINTEUSTATIUS", "SABA"}:
            definition = self.by_id["BES"]
            reasons.append("Caribbean Netherlands island overrides country-level NL selection.")
        elif context.country_code:
            definition = self._lookup(context.country_code)
            reasons.append("Resolved from ISO-style country or territory code.")
        elif context.country_name:
            definition = self._lookup(context.country_name)
            reasons.append("Resolved from country or territory name.")
        elif context.island:
            definition = self._lookup(context.island)
            reasons.append("Resolved from island name.")
        else:
            raise ValueError("Location context contains no jurisdiction signal.")

        local_scope = context.island.strip() if context.island else None
        overlays = list(definition.default_overlays)
        if island_key and island_key in definition.island_overlays:
            overlays.extend(definition.island_overlays[island_key])
            reasons.append("Applied island-specific engineering overlays.")

        unique_overlays = tuple(dict.fromkeys(overlays))
        return JurisdictionSelection(
            jurisdiction_id=definition.id,
            jurisdiction_name=definition.name,
            legal_codepack_manifest=definition.legal_codepack_manifest,
            foundation_profile=definition.foundation_profile,
            local_scope=local_scope,
            overlays=unique_overlays,
            confidence="high",
            reasons=tuple(reasons),
            legal_mixing_blocked=True,
        )

    def ensure_single_primary(
        self,
        selections: tuple[JurisdictionSelection, ...],
    ) -> None:
        jurisdictions = {selection.jurisdiction_id for selection in selections}
        if len(jurisdictions) > 1:
            raise ValueError(
                "Phoenix may not silently mix primary legal codepacks from "
                f"different jurisdictions: {sorted(jurisdictions)}"
            )

    def _lookup(self, value: str) -> JurisdictionDefinition:
        key = normalise_alias(value)
        try:
            return self.aliases[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported jurisdiction signal: {value!r}") from exc
