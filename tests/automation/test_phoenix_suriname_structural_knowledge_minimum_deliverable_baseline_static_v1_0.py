import json
import unittest
from pathlib import Path


class SurinameBaselineStaticTests(unittest.TestCase):
    def test_reference_catalog_has_three_user_sources(self):
        p = Path(__file__).resolve().parents[2] / "configs/phoenix/suriname_structural_reference_evidence_catalog_v1_0.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(len(data["references"]), 3)

    def test_drawing_reference_is_fifteen_sheets(self):
        p = Path(__file__).resolve().parents[2] / "configs/phoenix/building_minimum_deliverable_baseline_v1_0.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(data["drawing_baseline"]["reference_sheet_count"], 15)

    def test_professional_auto_approval_disabled(self):
        p = Path(__file__).resolve().parents[2] / "configs/phoenix/suriname_structural_knowledge_policy_v1_0.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertFalse(data["principles"]["automatic_professional_approval"])

    def test_session_hook_present(self):
        p = Path(__file__).resolve().parents[2] / "phoenix/autonomy/session_adapters.py"
        text = p.read_text(encoding="utf-8")
        self.assertIn("PHOENIX_SURINAME_MINIMUM_DELIVERABLE_BASELINE_HOOK_v1_0", text)


if __name__ == "__main__":
    unittest.main()
