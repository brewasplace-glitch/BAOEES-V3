from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.source_mapping import (
    MappingStatus,
    RuleMappingEngine,
    SourceAcquisitionPlanner,
    SourceMappingRegistry,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "configs" / "phoenix" / "source_catalogs" / "foundations"
MAPPING_DIR = ROOT / "configs" / "phoenix" / "rule_mappings" / "foundations"


class SourceMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = SourceMappingRegistry()
        self.planner = SourceAcquisitionPlanner()
        self.engine = RuleMappingEngine()

    def test_six_jurisdiction_catalogs_load(self) -> None:
        catalogs = self.registry.load_source_catalog_directory(CATALOG_DIR)
        self.assertEqual(6, len(catalogs))
        self.assertEqual(
            {"NL-EU", "SR", "BES", "AW", "CW", "SX"},
            {catalog.jurisdiction_id for catalog in catalogs},
        )

    def test_six_mapping_foundations_load(self) -> None:
        mappings = self.registry.load_mapping_directory(MAPPING_DIR)
        self.assertEqual(6, len(mappings))

    def test_discovered_source_creates_nonexecuting_verification_task(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "sr_source_catalog_v1_0.json"
        )
        tasks = self.planner.create_plan(catalog)
        self.assertEqual("verify_metadata", tasks[0].action.value)
        self.assertFalse(tasks[0].automatic_execution)

    def test_source_uri_with_credentials_is_rejected(self) -> None:
        data = json.loads(
            (CATALOG_DIR / "sr_source_catalog_v1_0.json").read_text(encoding="utf-8")
        )
        data["sources"][0]["canonical_uri"] = "https://user:secret@example.org/source"
        with self.assertRaises(ValueError):
            self.registry.load_source_catalog_dict(data)

    def test_cross_jurisdiction_pair_is_rejected(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "sr_source_catalog_v1_0.json"
        )
        mapping = self.registry.load_mapping_set(
            MAPPING_DIR / "aw_rule_mapping_v1_0.json"
        )
        with self.assertRaises(ValueError):
            self.registry.validate_pair(catalog, mapping)

    def test_unknown_source_mapping_is_rejected(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "sr_source_catalog_v1_0.json"
        )
        data = json.loads(
            (MAPPING_DIR / "sr_rule_mapping_v1_0.json").read_text(encoding="utf-8")
        )
        data["mappings"] = [
            {
                "id": "PHX-MAP-SR-TEST-001",
                "jurisdiction_id": "SR",
                "phoenix_rule_id": "PHX-SR-RULE-001",
                "source_id": "PHX-SOURCE-SR-UNKNOWN",
                "locator": "article 1",
                "status": "draft",
            }
        ]
        mapping = self.registry.load_mapping_set_dict(data)
        with self.assertRaises(ValueError):
            self.registry.validate_pair(catalog, mapping)

    def test_foundations_are_not_activation_eligible(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "nl_eu_source_catalog_v1_0.json"
        )
        mapping = self.registry.load_mapping_set(
            MAPPING_DIR / "nl_eu_rule_mapping_v1_0.json"
        )
        assessment = self.engine.assess_activation(catalog, mapping)
        self.assertFalse(assessment.eligible)
        self.assertTrue(assessment.reasons)

    def test_verified_and_approved_synthetic_pair_is_eligible(self) -> None:
        catalog_data = json.loads(
            (CATALOG_DIR / "sr_source_catalog_v1_0.json").read_text(encoding="utf-8")
        )
        catalog_data["status"] = "validated"
        source = catalog_data["sources"][0]
        source["status"] = "verified"
        source["verified_at"] = "2026-07-26T12:00:00Z"
        source["verified_by"] = "Test reviewer"
        catalog = self.registry.load_source_catalog_dict(catalog_data)

        mapping_data = json.loads(
            (MAPPING_DIR / "sr_rule_mapping_v1_0.json").read_text(encoding="utf-8")
        )
        mapping_data["status"] = "validated"
        mapping_data["required_rule_ids"] = ["PHX-SR-RULE-001"]
        mapping_data["mappings"] = [
            {
                "id": "PHX-MAP-SR-TEST-001",
                "jurisdiction_id": "SR",
                "phoenix_rule_id": "PHX-SR-RULE-001",
                "source_id": source["id"],
                "locator": "article 1",
                "status": "approved",
                "confidence": "high",
                "reviewer": "Test reviewer",
                "reviewed_at": "2026-07-26T12:00:00Z",
            }
        ]
        mapping = self.registry.load_mapping_set_dict(mapping_data)
        assessment = self.engine.assess_activation(catalog, mapping)
        self.assertTrue(assessment.eligible)

    def test_catalog_and_mapping_fingerprints_are_deterministic(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "bes_source_catalog_v1_0.json"
        )
        mapping = self.registry.load_mapping_set(
            MAPPING_DIR / "bes_rule_mapping_v1_0.json"
        )
        self.assertEqual(
            self.registry.fingerprint_catalog(catalog),
            self.registry.fingerprint_catalog(catalog),
        )
        self.assertEqual(
            self.registry.fingerprint_mapping_set(mapping),
            self.registry.fingerprint_mapping_set(mapping),
        )

    def test_assessment_export(self) -> None:
        catalog = self.registry.load_source_catalog(
            CATALOG_DIR / "sx_source_catalog_v1_0.json"
        )
        mapping = self.registry.load_mapping_set(
            MAPPING_DIR / "sx_rule_mapping_v1_0.json"
        )
        assessment = self.engine.assess_activation(catalog, mapping)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_assessment(
                assessment,
                Path(tmp) / "assessment.json",
            )
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("SX", data["jurisdiction_id"])
        self.assertIn("fingerprint_sha256", data)

    def test_duplicate_semantic_mapping_is_rejected(self) -> None:
        data = json.loads(
            (MAPPING_DIR / "sr_rule_mapping_v1_0.json").read_text(encoding="utf-8")
        )
        mapping = {
            "id": "PHX-MAP-SR-DUP-001",
            "jurisdiction_id": "SR",
            "phoenix_rule_id": "PHX-SR-RULE-001",
            "source_id": "PHX-SOURCE-SR-FOUNDATION",
            "locator": "article 1",
            "status": "draft",
        }
        data["mappings"] = [mapping, {**mapping, "id": "PHX-MAP-SR-DUP-002"}]
        with self.assertRaises(ValueError):
            self.registry.load_mapping_set_dict(data)


if __name__ == "__main__":
    unittest.main()
