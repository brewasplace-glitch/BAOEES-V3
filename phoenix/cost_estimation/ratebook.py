"""Rate-book loading, validation and deterministic fingerprinting."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .models import RateBook, RateBookStatus, RateItem, RateSelector

_SAFE_ID = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_ALLOWED_UNITS = {"ea", "m", "m2", "m3", "kg"}


class RateBookLoader:
    def load_file(self, path: str | Path) -> RateBook:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Rate-book root must be a JSON object.")
        return self.load_dict(payload)

    def load_dict(self, payload: Mapping[str, Any]) -> RateBook:
        ratebook_id = self._required_text(payload, "id")
        self._validate_id(ratebook_id, "rate-book id")
        currency = self._required_text(payload, "currency").upper()
        if not _CURRENCY.fullmatch(currency):
            raise ValueError(f"Invalid ISO-style currency code: {currency}")
        price_date = self._required_text(payload, "price_date")
        date.fromisoformat(price_date)

        raw_rates = payload.get("rates")
        if not isinstance(raw_rates, list) or not raw_rates:
            raise ValueError("Rate book requires at least one rate item.")
        rates = tuple(self._load_rate(item, currency) for item in raw_rates)
        ids = [item.id for item in rates]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate rate-item identifiers are not allowed.")

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("Rate-book metadata must be an object.")

        return RateBook(
            id=ratebook_id,
            name=self._required_text(payload, "name"),
            version=self._required_text(payload, "version"),
            status=RateBookStatus(self._required_text(payload, "status")),
            currency=currency,
            price_date=price_date,
            jurisdiction=self._required_text(payload, "jurisdiction"),
            location_profile=self._required_text(payload, "location_profile"),
            rates=rates,
            source_reference=self._optional_text(payload, "source_reference"),
            metadata=dict(metadata),
        )

    def fingerprint(self, ratebook: RateBook) -> str:
        payload = json.dumps(
            ratebook.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _load_rate(self, payload: Any, currency: str) -> RateItem:
        if not isinstance(payload, Mapping):
            raise ValueError("Every rate item must be an object.")
        rate_id = self._required_text(payload, "id")
        self._validate_id(rate_id, "rate item id")
        unit = self._required_text(payload, "unit")
        if unit not in _ALLOWED_UNITS:
            raise ValueError(f"{rate_id}: unsupported quantity unit {unit!r}.")

        raw_selector = payload.get("selector")
        if not isinstance(raw_selector, Mapping):
            raise ValueError(f"{rate_id}: selector must be an object.")
        selector = RateSelector(
            quantity_types=self._string_tuple(raw_selector, "quantity_types"),
            categories=self._string_tuple(raw_selector, "categories"),
            work_sections=self._string_tuple(raw_selector, "work_sections"),
            materials=self._string_tuple(raw_selector, "materials"),
            source_models=self._string_tuple(raw_selector, "source_models"),
        )
        if selector.specificity == 0:
            raise ValueError(f"{rate_id}: selector must constrain at least one field.")

        rate_currency = str(payload.get("currency", currency)).upper()
        if rate_currency != currency:
            raise ValueError(
                f"{rate_id}: mixed currencies are not allowed in one rate book."
            )

        components = {}
        for key in (
            "material_rate",
            "labor_rate",
            "equipment_rate",
            "subcontract_rate",
            "other_rate",
            "waste_percent",
        ):
            value = payload.get(key, 0.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{rate_id}: {key} must be numeric.")
            if value < 0:
                raise ValueError(f"{rate_id}: {key} must not be negative.")
            components[key] = float(value)

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError(f"{rate_id}: metadata must be an object.")

        return RateItem(
            id=rate_id,
            cost_code=self._required_text(payload, "cost_code"),
            description=self._required_text(payload, "description"),
            unit=unit,
            selector=selector,
            material_rate=components["material_rate"],
            labor_rate=components["labor_rate"],
            equipment_rate=components["equipment_rate"],
            subcontract_rate=components["subcontract_rate"],
            other_rate=components["other_rate"],
            waste_percent=components["waste_percent"],
            source_reference=self._optional_text(payload, "source_reference"),
            metadata=dict(metadata),
        )

    @staticmethod
    def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
        value = payload.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(f"Selector {key} must be a list of non-empty strings.")
        return tuple(sorted(set(item.strip() for item in value)))

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
