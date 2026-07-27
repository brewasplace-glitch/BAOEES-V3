from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.local_app.dashboard_adapter import DashboardAdapter
from phoenix.local_app.models import DashboardCandidate, RuntimeJob
from phoenix.local_app.workflow_registry import WorkflowRegistry


ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "configs/phoenix/local_one_click_app_v1_0_0.json").read_text(
        encoding="utf-8"
    )
)


class PhoenixLocalOneClickAppTests(unittest.TestCase):
    def test_local_host_only(self):
        self.assertEqual("127.0.0.1", CONFIG["host"])

    def test_default_port(self):
        self.assertEqual(8765, CONFIG["preferred_port"])

    def test_four_workflows_registered(self):
        self.assertEqual(4, len(CONFIG["workflows"]))

    def test_real_production_workflow_is_visible(self):
        self.assertIn(
            "real_concept_drawings_reports",
            {item["id"] for item in CONFIG["workflows"]},
        )

    def test_open_targets_registered(self):
        self.assertGreaterEqual(len(CONFIG["open_targets"]), 6)

    def test_candidate_serialization(self):
        value = DashboardCandidate("index.html", 10, ("Phoenix",)).to_dict()
        self.assertEqual(10, value["score"])
        self.assertEqual(["Phoenix"], value["matched_markers"])

    def test_runtime_job_serialization(self):
        job = RuntimeJob(
            job_id="abc",
            workflow_id="test",
            label="Test",
            status="QUEUED",
            started_at="2026-07-27T00:00:00+00:00",
            output_dir="out",
            log_path="log",
        )
        self.assertEqual("abc", job.to_dict()["job_id"])

    def test_existing_dashboard_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "dashboard.html").write_text(
                "<html><body>PROJECT PHOENIX START PROJECTANALYSE Autonomous Project Mode Bouw Civiel Infra</body></html>",
                encoding="utf-8",
            )
            adapter = DashboardAdapter(repo, CONFIG)
            selected = adapter.select()
            self.assertIsNotNone(selected)
            self.assertEqual("dashboard.html", selected.relative_path)

    def test_low_score_dashboard_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "index.html").write_text("<html></html>", encoding="utf-8")
            adapter = DashboardAdapter(repo, CONFIG)
            self.assertIsNone(adapter.select())

    def test_bridge_is_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "start_dashboard.html").write_text(
                "<html><body>PROJECT PHOENIX START PROJECTANALYSE Autonomous Project Mode Bouw Civiel Infra</body></html>",
                encoding="utf-8",
            )
            rendered, info = DashboardAdapter(repo, CONFIG).render("TOKEN")
            self.assertIn("phoenix-local-bridge", rendered)
            self.assertIn("TOKEN", rendered)
            self.assertEqual("REUSED_EXISTING_DASHBOARD", info["source_kind"])

    def test_workflow_registry_marks_known_runners_available(self):
        registry = WorkflowRegistry(ROOT, CONFIG)
        described = {item["id"]: item for item in registry.describe()}
        self.assertTrue(described["bb35_full_concept_simulation"]["available"])
        self.assertTrue(described["bb35_integrated_concept_dossier"]["available"])
        self.assertTrue(described["bb35_project_leader_review"]["available"])

    def test_production_workflow_is_available(self):
        registry = WorkflowRegistry(ROOT, CONFIG)
        described = {item["id"]: item for item in registry.describe()}
        self.assertTrue(described["real_concept_drawings_reports"]["available"])

    def test_start_script_exists(self):
        self.assertTrue((ROOT / "START_PHOENIX.ps1").is_file())

    def test_cmd_script_exists(self):
        self.assertTrue((ROOT / "START_PHOENIX.cmd").is_file())

    def test_stop_script_exists(self):
        self.assertTrue((ROOT / "STOP_PHOENIX.ps1").is_file())

    def test_shortcut_script_exists(self):
        self.assertTrue(
            (ROOT / "scripts/phoenix_local_app/CREATE_DESKTOP_SHORTCUT.ps1").is_file()
        )

    def test_fallback_dashboard_exists(self):
        self.assertTrue(
            (ROOT / "phoenix/local_app/static/fallback_dashboard.html").is_file()
        )

    def test_fallback_contains_start_button(self):
        content = (
            ROOT / "phoenix/local_app/static/fallback_dashboard.html"
        ).read_text(encoding="utf-8")
        self.assertIn("START PROJECTANALYSE", content)

    def test_no_shell_execution_in_workflow_registry(self):
        content = (
            ROOT / "phoenix/local_app/workflow_registry.py"
        ).read_text(encoding="utf-8")
        self.assertIn("shell=False", content)

    def test_server_requires_token_for_post(self):
        content = (ROOT / "phoenix/local_app/server.py").read_text(encoding="utf-8")
        self.assertIn("X-Phoenix-Token", content)

    def test_server_rejects_external_bind(self):
        content = (
            ROOT / "runners/PROJECT_PHOENIX_local_one_click_app_v1_0_0.py"
        ).read_text(encoding="utf-8")
        self.assertIn("host != \"127.0.0.1\"", content)

    def test_config_has_candidate_limit(self):
        self.assertEqual(500, CONFIG["dashboard"]["max_candidate_files"])

    def test_config_has_minimum_score(self):
        self.assertEqual(8, CONFIG["dashboard"]["minimum_score"])

    def test_dashboard_markers_include_autonomous_mode(self):
        self.assertIn(
            "Autonomous Project Mode",
            CONFIG["dashboard"]["content_markers"],
        )

    def test_runtime_root_is_under_outputs(self):
        self.assertTrue(CONFIG["runtime_root"].startswith("outputs/runtime/"))

    def test_project_folder_target_exists(self):
        target = next(item for item in CONFIG["open_targets"] if item["id"] == "project_folder")
        self.assertEqual(".", target["relative_path"])


if __name__ == "__main__":
    unittest.main()
