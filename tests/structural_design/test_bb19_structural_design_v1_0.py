from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.structural_design import StructuralDesignEngine


def building_model() -> dict:
    return {
        "project_id": "PHX-STRUCT-001",
        "elements": [
            {
                "id": "ELM-FOUND-001",
                "category": "foundation",
                "level_id": "LVL-00",
                "geometry": {"length_m": 6.0},
                "material": {"name": "concrete"},
                "properties": {},
            },
            {
                "id": "ELM-BEAM-001",
                "category": "beam",
                "level_id": "LVL-00",
                "geometry": {"length_m": 5.0},
                "material": {"name": "steel"},
                "properties": {"section": {"name": "IPE200"}},
            },
            {
                "id": "ELM-DOOR-001",
                "category": "door",
                "level_id": "LVL-00",
                "geometry": {},
                "material": {},
                "properties": {},
            },
        ],
    }


class StructuralDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = StructuralDesignEngine()

    def test_structural_members_are_filtered_from_building_model(self) -> None:
        model = self.engine.create_model(building_model())
        self.assertEqual(2, len(model.members))
        self.assertNotIn("ELM-DOOR-001", {item.source_element_id for item in model.members})

    def test_foundation_creates_support_interface(self) -> None:
        model = self.engine.create_model(building_model())
        self.assertEqual(1, len(model.supports))

    def test_default_load_cases_and_combinations(self) -> None:
        model = self.engine.create_model(building_model())
        self.assertEqual({"LC-G", "LC-Q", "LC-W"}, {item.id for item in model.load_cases})
        self.assertEqual(2, len(model.combinations))

    def test_validation_warns_about_placeholder_code_factors(self) -> None:
        model = self.engine.create_model(building_model())
        issues = self.engine.validate(model)
        self.assertIn("SDE-CODE-001", {item.code for item in issues})

    def test_empty_structural_model_fails_validation(self) -> None:
        model = self.engine.create_model({"project_id": "EMPTY", "elements": []})
        issues = self.engine.validate(model)
        self.assertIn("SDE-MEMBER-001", {item.code for item in issues})

    def test_supported_handoffs(self) -> None:
        model = self.engine.create_model(building_model())
        for engine in ("openseespy", "calculix", "scia"):
            handoff = self.engine.create_handoff(model, engine, "model.json")
            self.assertEqual(engine, handoff.engine)
            self.assertTrue(handoff.non_certifying)

    def test_unknown_handoff_is_rejected(self) -> None:
        model = self.engine.create_model(building_model())
        with self.assertRaises(ValueError):
            self.engine.create_handoff(model, "unknown", "model.json")

    def test_model_export_contains_validation_issues(self) -> None:
        model = self.engine.create_model(building_model())
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_model(model, Path(tmp) / "structural.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("validation_issues", data)

    def test_fingerprint_is_deterministic(self) -> None:
        first = self.engine.create_model(building_model())
        second = self.engine.create_model(building_model())
        self.assertEqual(
            first.metadata["structural_model_fingerprint_sha256"],
            second.metadata["structural_model_fingerprint_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
