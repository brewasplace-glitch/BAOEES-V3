"""Regional structural profile registry for Project Phoenix.

Profiles describe jurisdictional context and mandatory confirmation gates. They do
not silently declare a calculation standard to be legally accepted.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

SUPPORTED_CODES = ("SUR", "BES-BON", "BES-EUX", "BES-SAB", "ABW", "CUR", "SXM")

class RegionalStructuralProfileRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self.data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        profiles = self.data.get("profiles", {})
        missing = [code for code in SUPPORTED_CODES if code not in profiles]
        if missing:
            raise ValueError(f"Missing structural profiles: {missing}")
        self.profiles = profiles

    def get(self, code: str) -> Mapping[str, Any]:
        normalized = code.strip().upper()
        if normalized not in self.profiles:
            raise KeyError(f"Unsupported jurisdiction: {code}")
        return self.profiles[normalized]

    def describe(self) -> list[dict[str, Any]]:
        return [dict(self.profiles[code]) for code in SUPPORTED_CODES]

    def validate_confirmation(self, code: str, confirmation: Mapping[str, Any]) -> list[str]:
        profile = self.get(code)
        errors = []
        if confirmation.get("jurisdiction_code", "").upper() != code.upper():
            errors.append("jurisdiction_code does not match selected profile")
        if not confirmation.get("structural_engineer_basis_confirmed"):
            errors.append("structural_engineer_basis_confirmed is required")
        if not str(confirmation.get("design_standard_reference", "")).strip():
            errors.append("design_standard_reference is required")
        for item in profile["required_environment_inputs"]:
            key = item.split()[0]
            if key not in confirmation and item not in confirmation:
                errors.append(f"required environment input missing: {item}")
        for item in profile["required_hazard_inputs"]:
            key = item.split()[0]
            if key not in confirmation and item not in confirmation:
                errors.append(f"required hazard input missing: {item}")
        return errors
