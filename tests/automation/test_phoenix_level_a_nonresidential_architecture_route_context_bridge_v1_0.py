import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.architectural_bootstrap import generate_architectural_bootstrap
from phoenix.autonomy.nonresidential_session_architecture_bridge_v1_0 import (
    ROUTE_ID,
    resolve_nonresidential_session_architecture,
)

REPO = Path(__file__).resolve().parents[2]
SESSION_ADAPTERS = REPO / "phoenix" / "autonomy" / "session_adapters.py"
BINDING = "configs/projects/moskee_bunschoten_e2e_real_project_binding_v1_1.json"


class NonresidentialSessionArchitectureBridgeTests(unittest.TestCase):
    def context(self, output_dir):
        return {
            "repository": REPO,
            "output_dir": Path(output_dir),
            "project_id": "configs-projects-moskee_bunschoten_e2e_real_project_binding_v1_1.json",
            "session": {
                "selected_project": BINDING,
                "project_type": "BOUW",
                "project_mode": "autonomous",
            },
        }

    def test_moskee_binding_resolves_existing_nonresidential_architecture(self):
        with tempfile.TemporaryDirectory() as folder:
            result = resolve_nonresidential_session_architecture(self.context(folder))
            self.assertTrue(result["matched"])
            self.assertEqual(result["status"], "PASSED", result)
            self.assertEqual(result["route"], ROUTE_ID)
            self.assertTrue(result["model"]["storeys"])
            self.assertEqual(result["model"]["production_release"], "LOCKED")
            self.assertFalse(result["model"]["professional_approval"])
            self.assertTrue(Path(result["model_source_path"]).is_file())
            self.assertIn("moskee_bunschoten", Path(result["model_source_path"]).name)
            self.assertTrue(Path(result["evidence_path"]).is_file())
            payload = json.loads(Path(result["evidence_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["route"], ROUTE_ID)
            self.assertEqual(payload["for_construction"], "LOCKED")

    def test_lossless_view_has_generic_detailed_collections(self):
        with tempfile.TemporaryDirectory() as folder:
            result = resolve_nonresidential_session_architecture(self.context(folder))
            detailed = result["detailed_elements"]
            self.assertTrue(detailed["storeys"])
            for storey in detailed["storeys"]:
                self.assertIn("walls", storey)
                self.assertIn("doors", storey)
                self.assertIn("windows", storey)
                self.assertIn("stairs", storey)

    def test_existing_unknown_use_still_blocks(self):
        result = generate_architectural_bootstrap(
            project_id="P",
            project_type="BOUW",
            brief="Ontwerp een onbekend gebouw",
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason, "ARCHITECTURAL_USE_TYPE_REQUIRED")

    def test_route_bridge_runs_before_residential_bootstrap(self):
        text = SESSION_ADAPTERS.read_text(encoding="utf-8-sig")
        call = "resolve_nonresidential_session_architecture(ctx)"
        bootstrap = "generated = generate_architectural_bootstrap("
        self.assertIn(call, text)
        self.assertIn(bootstrap, text)
        self.assertLess(text.index(call), text.index(bootstrap))

    def test_no_new_nonresidential_architecture_engine(self):
        text = SESSION_ADAPTERS.read_text(encoding="utf-8-sig")
        self.assertIn("NONRESIDENTIAL_REUSE_V1", (
            REPO / "phoenix/autonomy/nonresidential_session_architecture_bridge_v1_0.py"
        ).read_text(encoding="utf-8-sig"))
        self.assertTrue(
            (REPO / "phoenix/architecture/nonresidential_real_project_orchestration_v1_0.py").is_file()
        )


if __name__ == "__main__":
    unittest.main()
