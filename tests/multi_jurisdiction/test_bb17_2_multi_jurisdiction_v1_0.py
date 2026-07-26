from __future__ import annotations

import json
import unittest
from pathlib import Path

from phoenix.building_code import CodeProfileRegistry
from phoenix.codepack_governance import ActivationState, CodepackRegistry, ReviewStatus
from phoenix.multi_jurisdiction import (
    JurisdictionRegistry,
    JurisdictionResolver,
    LocationContext,
)

ROOT = Path(__file__).resolve().parents[2]
JURISDICTIONS = ROOT / "configs/phoenix/jurisdictions"
FOUNDATIONS = ROOT / "configs/phoenix/codepacks/foundations"
PROFILES = ROOT / "configs/phoenix/building_code_profiles/foundations"


class MultiJurisdictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = JurisdictionRegistry()
        self.definitions = self.registry.load_directory(JURISDICTIONS)
        self.resolver = JurisdictionResolver(self.definitions)

    def test_european_netherlands_selection(self) -> None:
        selection = self.resolver.resolve(LocationContext(country_code="NL"))
        self.assertEqual("NL-EU", selection.jurisdiction_id)

    def test_paramaribo_selects_suriname(self) -> None:
        selection = self.resolver.resolve(
            LocationContext(country_code="SR", district="Paramaribo")
        )
        self.assertEqual("SR", selection.jurisdiction_id)
        self.assertIn("TROPICAL-HUMID", selection.overlays)

    def test_bonaire_overrides_nl_and_adds_island_overlay(self) -> None:
        selection = self.resolver.resolve(
            LocationContext(country_code="NL", island="Bonaire")
        )
        self.assertEqual("BES", selection.jurisdiction_id)
        self.assertIn("ARID-CARIBBEAN", selection.overlays)

    def test_sint_eustatius_and_saba_select_bes(self) -> None:
        for island in ("Sint Eustatius", "Saba"):
            selection = self.resolver.resolve(LocationContext(island=island))
            self.assertEqual("BES", selection.jurisdiction_id)
            self.assertIn("VOLCANIC-SLOPE", selection.overlays)

    def test_aruba_curacao_and_sint_maarten_are_separate(self) -> None:
        expected = {"AW": "AW", "CW": "CW", "SX": "SX"}
        for signal, jurisdiction in expected.items():
            selection = self.resolver.resolve(LocationContext(country_code=signal))
            self.assertEqual(jurisdiction, selection.jurisdiction_id)

    def test_curacao_diacritic_alias(self) -> None:
        selection = self.resolver.resolve(LocationContext(country_name="Curaçao"))
        self.assertEqual("CW", selection.jurisdiction_id)

    def test_unknown_jurisdiction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.resolver.resolve(LocationContext(country_code="ZZ"))

    def test_primary_legal_codepacks_may_not_mix(self) -> None:
        nl = self.resolver.resolve(LocationContext(country_code="NL"))
        sr = self.resolver.resolve(LocationContext(country_code="SR"))
        with self.assertRaises(ValueError):
            self.resolver.ensure_single_primary((nl, sr))

    def test_all_engineering_overlays_are_registered(self) -> None:
        overlays = self.registry.load_overlays(
            JURISDICTIONS / "engineering_overlays_v1_0.json"
        )
        for definition in self.definitions:
            for overlay in definition.default_overlays:
                self.assertIn(overlay, overlays)
            for island_overlays in definition.island_overlays.values():
                for overlay in island_overlays:
                    self.assertIn(overlay, overlays)

    def test_foundation_manifests_are_draft_and_inactive(self) -> None:
        manifests = CodepackRegistry().load_directory(FOUNDATIONS)
        self.assertEqual(6, len(manifests))
        for manifest in manifests:
            self.assertEqual(ReviewStatus.DRAFT, manifest.review_status)
            self.assertEqual(ActivationState.INACTIVE, manifest.activation_state)
            self.assertFalse(manifest.regulatory_claim)

    def test_foundation_profiles_load_in_bb17_and_have_no_rules(self) -> None:
        profile_registry = CodeProfileRegistry()
        profiles = [profile_registry.load_file(path) for path in sorted(PROFILES.glob("*.json"))]
        self.assertEqual(6, len(profiles))
        for profile in profiles:
            self.assertEqual(0, len(profile.rules))
            self.assertFalse(profile.metadata["legal_compliance_claim"])

    def test_registry_fingerprint_is_deterministic(self) -> None:
        self.assertEqual(
            self.registry.fingerprint(self.definitions),
            self.registry.fingerprint(self.definitions),
        )


if __name__ == "__main__":
    unittest.main()
