from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import unittest

from phoenix.autonomy.canonical_v4_structural_bridge import (
    normalize_canonical_v4_for_structural_session,
)


def canonical_model() -> dict:
    return {
        "schema_version": "phoenix.architectural-model/4.0.0",
        "project_id": "TEST-VAR-E",
        "levels": [
            {"id": "L00", "name": "Ground", "elevation_m": 0.0, "floor_to_floor_m": 3.3},
            {"id": "L01", "name": "Upper", "elevation_m": 3.3, "floor_to_floor_m": 3.0},
        ],
        "walls": [
            {"id": "W1", "level_id": "L00", "start": [0,0], "end": [10,0], "height_m": 3.3, "thickness_m": 0.3, "external": True},
            {"id": "W2", "level_id": "L00", "start": [10,0], "end": [10,7], "height_m": 3.3, "thickness_m": 0.3, "external": True},
            {"id": "W3", "level_id": "L01", "start": [0,0], "end": [10,0], "height_m": 3.0, "thickness_m": 0.3, "external": True},
        ],
        "spaces": [
            {"id": "S1", "level_id": "L00", "polygon": [[0,0],[10,0],[10,7],[0,7],[0,0]]},
            {"id": "S2", "level_id": "L01", "polygon": [[1,1],[9,1],[9,6],[1,6],[1,1]]},
        ],
        "openings": [
            {"id": "D1", "kind": "door", "wall_id": "W1", "width_m": 1.2, "height_m": 2.3},
        ],
        "candidate_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }


class CanonicalV4StructuralBridgeTests(unittest.TestCase):
    def normalize(self, value: dict | None = None):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "canonical.json"
            source.write_text(
                json.dumps(value or canonical_model(), indent=2) + "\n",
                encoding="utf-8",
            )
            return normalize_canonical_v4_for_structural_session(
                value or canonical_model(),
                project_id="TEST-PROJECT",
                source_path=source,
                recommended_variant_id="E",
            )

    def test_storey_relationships_are_preserved(self):
        value, stats = self.normalize()
        self.assertEqual([s["storey_id"] for s in value["storeys"]], ["L00", "L01"])
        self.assertEqual(stats["wall_count"], 3)
        self.assertEqual(stats["space_count"], 2)

    def test_wall_identity_aliases_are_lossless(self):
        value, _ = self.normalize()
        walls = [w for s in value["storeys"] for w in s["walls"]]
        self.assertTrue(all(w["element_id"] == w["id"] for w in walls))
        self.assertTrue(all(w["storey_id"] == w["level_id"] for w in walls))

    def test_space_identity_aliases_are_lossless(self):
        value, _ = self.normalize()
        spaces = [r for s in value["storeys"] for r in s["spaces"]]
        self.assertTrue(all(r["element_id"] == r["id"] for r in spaces))
        self.assertTrue(all(r["space_id"] == r["id"] for r in spaces))
        self.assertTrue(all(r["storey_id"] == r["level_id"] for r in spaces))

    def test_wall_lengths_derive_from_existing_geometry(self):
        value, _ = self.normalize()
        walls = [w for s in value["storeys"] for w in s["walls"]]
        by_id = {w["id"]: w for w in walls}
        self.assertEqual(by_id["W1"]["length_m"], 10.0)
        self.assertEqual(by_id["W2"]["length_m"], 7.0)

    def test_space_bbox_is_derived_only_from_rectangular_polygon(self):
        value, _ = self.normalize()
        spaces = [r for s in value["storeys"] for r in s["spaces"]]
        by_id = {r["id"]: r for r in spaces}
        self.assertEqual((by_id["S1"]["x_m"], by_id["S1"]["y_m"]), (0.0, 0.0))
        self.assertEqual((by_id["S1"]["width_m"], by_id["S1"]["depth_m"]), (10.0, 7.0))

    def test_nonrectangular_space_is_fail_safe(self):
        model = canonical_model()
        model["spaces"][0]["polygon"] = [[0,0],[10,0],[8,7],[0,7],[0,0]]
        with self.assertRaisesRegex(RuntimeError, "niet axis-aligned rechthoekig"):
            self.normalize(model)

    def test_release_locks_are_preserved(self):
        value, _ = self.normalize()
        self.assertEqual(value["production_release"], "LOCKED")
        self.assertEqual(value["for_construction"], "LOCKED")
        self.assertTrue(value["professional_review_required"])

    def test_original_canonical_arrays_remain_present(self):
        value, _ = self.normalize()
        self.assertIsInstance(value["levels"], list)
        self.assertIsInstance(value["walls"], list)
        self.assertIsInstance(value["spaces"], list)
        self.assertIsInstance(value["openings"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
