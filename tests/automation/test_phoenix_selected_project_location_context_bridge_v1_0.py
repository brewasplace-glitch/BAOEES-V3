import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.selected_project_context_bridge_v1_0 import (
    merge_selected_project_facts,
    resolve_selected_project_context,
)

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "phoenix" / "autonomy" / "session_adapters.py"
MOSKEE = "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"


class SelectedProjectContextBridgeTests(unittest.TestCase):
    def test_moskee_binding_exposes_explicit_location_and_country(self):
        result = resolve_selected_project_context({
            "repository": ROOT,
            "session": {"selected_project": MOSKEE},
        })
        self.assertEqual(result["status"], "PASSED", result)
        self.assertEqual(result["facts"]["project_location"], "Bikkersweg 88, Bunschoten")
        self.assertEqual(result["facts"]["country_name"], "Nederland")
        self.assertEqual(result["facts"]["country_code"], "NL")
        self.assertFalse(result["jurisdiction_confirmed"])
        self.assertFalse(result["automatic_legal_conclusion"])

    def test_merge_does_not_overwrite_existing_resolved_fact(self):
        context = {"facts": {"project_location": "Explicit session location"}}
        bridge = {
            "status": "PASSED",
            "schema_version": "x",
            "source": "binding.json",
            "source_kind": "SELECTED_PROJECT_EXPLICIT_FACTS",
            "facts": {
                "project_location": "Binding location",
                "country_code": "NL",
            },
        }
        merged = merge_selected_project_facts(context, bridge)
        self.assertEqual(merged["facts"]["project_location"], "Explicit session location")
        self.assertEqual(merged["facts"]["country_code"], "NL")

    def test_unknown_country_name_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            project = repo / "project.json"
            project.write_text(
                '{"location":"Example place","country":"Unknownland"}',
                encoding="utf-8",
            )
            result = resolve_selected_project_context({
                "repository": repo,
                "session": {"selected_project": "project.json"},
            })
            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(result["facts"]["country_name"], "Unknownland")
            self.assertNotIn("country_code", result["facts"])

    def test_bridge_runs_before_location_intelligence(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        bridge = "resolve_selected_project_context(ctx)"
        location = "location_result=resolve_location_intelligence("
        self.assertIn(bridge, text)
        self.assertIn(location, text)
        self.assertLess(text.index(bridge), text.index(location))

    def test_permit_keeps_legal_conclusion_locked(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        self.assertIn('"automatic_permit_conclusion":False', text)
        self.assertIn('"release":"LOCKED"', text)


if __name__ == "__main__":
    unittest.main()
