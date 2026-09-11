import json
import tempfile
import unittest
from pathlib import Path

from phoenix.structural_input_gap.analyzer import _norm, render_markdown, PRELIMINARY_PASS


class TestPhoenix441AnijstraatGap(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(_norm("  A\n  B  "), "A B")

    def test_governance_markdown(self):
        data = {
            "project_id": "PHX-RP-ANIJSTRAAT-616",
            "status": PRELIMINARY_PASS,
            "source": {"name": "x.pdf", "page_count": 15, "sha256": "abc"},
            "tank": {"volume_m3": 2.0, "stored_water_weight_kN": 19.62},
            "authority_conflicts": [
                {"id": "CONFLICT-RINGBEAM-001", "topic": "ring_beam_section", "values": ["100 x 200 mm", "100 x 150 mm"]}
            ],
            "release_blockers": ["GEOTECH"],
            "next_stage_contract": {"stage": "STRUCTURAL_DERIVATION"},
        }
        md = render_markdown(data)
        self.assertIn("PRELIMINARY / NOT FOR CONSTRUCTION", md)
        self.assertIn("2.0 m³", md)
        self.assertIn("19.62 kN", md)


if __name__ == "__main__":
    unittest.main()
