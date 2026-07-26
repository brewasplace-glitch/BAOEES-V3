from __future__ import annotations

import json
import unittest
from pathlib import Path

from phoenix.bb35_pilots.moskee_bunschoten.scope_decision_b import (
    MoskeeScopeDecisionBValidator,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/projects/moskee_bunschoten_bb35_pilot_1.json"
DECISION = (
    ROOT
    / "inputs/pilots/moskee_bunschoten/"
    "scope_decision_B_v1_1_0.json"
)


class ScopeDecisionBTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.result = MoskeeScopeDecisionBValidator().validate(
            self.config,
            self.decision,
        )

    def test_option_b_is_authoritative(self) -> None:
        self.assertEqual(
            "B",
            self.config["project"]["authoritative_scope"][
                "selected_option"
            ],
        )

    def test_dimensions_are_7_by_10(self) -> None:
        scope = self.config["project"]["authoritative_scope"]
        self.assertEqual(7.0, scope["extension_width_m"])
        self.assertEqual(10.0, scope["extension_depth_m"])

    def test_footprint_is_70_square_metres(self) -> None:
        self.assertEqual(
            70.0,
            self.config["project"]["authoritative_scope"][
                "extension_footprint_m2"
            ],
        )

    def test_gross_extension_is_140_square_metres(self) -> None:
        self.assertEqual(
            140.0,
            self.config["project"]["authoritative_scope"][
                "gross_extension_area_m2"
            ],
        )

    def test_extension_has_two_storeys(self) -> None:
        self.assertEqual(
            2,
            self.config["project"]["authoritative_scope"][
                "number_of_extension_storeys"
            ],
        )

    def test_scope_conflict_is_resolved(self) -> None:
        conflict = next(
            item
            for item in self.config["verified_conflicts"]
            if item["conflict_id"] == "HBM-CONFLICT-001"
        )
        self.assertEqual("resolved", conflict["status"])
        self.assertFalse(conflict["blocking"])

    def test_20_square_metre_scope_is_superseded(self) -> None:
        statement = self.config["superseded_scope_statements"][0]
        self.assertEqual("superseded", statement["status"])

    def test_scope_propagates_to_required_modules(self) -> None:
        modules = set(
            self.config["mandatory_propagation"]["modules"]
        )
        self.assertTrue({
            "structural_design",
            "permit_and_bopa",
            "parking_and_traffic",
            "aerius",
            "cost_estimation",
            "technical_specification",
        }.issubset(modules))

    def test_decision_validation_passes(self) -> None:
        self.assertTrue(self.result["scope_decision_valid"])

    def test_pilot_moves_to_pending_inputs(self) -> None:
        self.assertEqual(
            "BLOCKED_PENDING_INPUTS",
            self.result["pilot_status"],
        )

    def test_bb36_remains_locked(self) -> None:
        self.assertFalse(self.result["bb36_unlock_allowed"])


if __name__ == "__main__":
    unittest.main()
