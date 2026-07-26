from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.codepack_governance import (
    ActivationState,
    CodepackGovernanceEngine,
    CodepackRegistry,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs/phoenix/codepacks/registry/phoenix_model_integrity_v1_0.json"


class CodepackGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CodepackRegistry()
        self.engine = CodepackGovernanceEngine()
        self.manifest = self.registry.load_file(MANIFEST)

    def test_validated_internal_baseline_is_eligible(self) -> None:
        decision = self.engine.activation_decision(
            self.manifest,
            as_of_date="2026-07-26",
        )
        self.assertTrue(decision.eligible)

    def test_unreviewed_active_codepack_is_rejected(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["review_status"] = "draft"
        with self.assertRaises(ValueError):
            self.registry.load_dict(data)

    def test_regulatory_active_codepack_requires_verified_source(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["id"] = "PHX-CODEPACK-REGULATORY-TEST"
        data["regulatory_claim"] = True
        data["sources"][0]["source_status"] = "identified"
        with self.assertRaises(ValueError):
            self.registry.load_dict(data)

    def test_inactive_foundation_may_use_identified_source(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["id"] = "PHX-CODEPACK-FOUNDATION-TEST"
        data["review_status"] = "draft"
        data["activation_state"] = "inactive"
        data["regulatory_claim"] = False
        data["reviewed_by"] = None
        data["reviewed_at"] = None
        data["sources"][0]["source_status"] = "identified"
        data["sources"][0].pop("effective_from", None)
        manifest = self.registry.load_dict(data)
        self.assertEqual(ActivationState.INACTIVE, manifest.activation_state)

    def test_unsafe_profile_path_is_rejected(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["profile_path"] = "../outside.json"
        with self.assertRaises(ValueError):
            self.registry.load_dict(data)

    def test_registry_fingerprint_is_deterministic(self) -> None:
        manifests = (self.manifest,)
        self.assertEqual(
            self.registry.fingerprint(manifests),
            self.registry.fingerprint(manifests),
        )

    def test_export_index_contains_active_codepack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.registry.export_index(
                (self.manifest,),
                Path(tmp) / "registry.json",
            )
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn(self.manifest.id, data["active_codepacks"])

    def test_single_active_guard(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["id"] = "PHX-CODEPACK-MODEL-INTEGRITY-DUP"
        duplicate = self.registry.load_dict(data)
        with self.assertRaises(ValueError):
            self.engine.ensure_single_active((self.manifest, duplicate))


if __name__ == "__main__":
    unittest.main()
