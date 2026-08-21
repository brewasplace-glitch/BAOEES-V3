from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from phoenix.local_app.architectural_orchestration_runtime import (
    ArchitecturalOrchestrationJob,
    ArchitecturalOrchestrationRuntime,
)

STRUCTURAL = [
    "calculations",
    "structural_drawings",
    "foundation_drawings",
    "structural_analysis",
    "foundation_design",
]

class StructuralSessionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name).resolve()
        (self.repo / "projects/runtime").mkdir(parents=True)
        (self.repo / "configs/phoenix").mkdir(parents=True)
        (self.repo / "runners").mkdir(parents=True)
        config = {
            "output_capability_map": {
                token: ["structural_engineering"] for token in STRUCTURAL
            }
        }
        config["output_capability_map"]["planning"] = ["cost_planning"]
        (self.repo / "configs/phoenix/autonomous_project_orchestrator_v1_0.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        (self.repo / "runners/PROJECT_PHOENIX_autonomous_session_orchestrator_v1_0_0.py").write_text(
            "print('fake')\n", encoding="utf-8"
        )
        self.runtime = ArchitecturalOrchestrationRuntime(self.repo)
        self.job = ArchitecturalOrchestrationJob(
            job_id="bridge-test",
            project_file="configs/projects/test.json",
            project_id="MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            status="RUNNING",
            started_at="2026-08-21T00:00:00+00:00",
            output_dir="projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            log_path="projects/runtime/_architectural_orchestration_jobs/test/workflow.log",
            command=["python"],
        )
        self.project = {
            "project_id": self.job.project_id,
            "requested_outputs": [*STRUCTURAL, "planning", "unmapped"],
            "metadata": {
                "phoenix_structural_capability_activation": {
                    "route": "structural_engineering"
                }
            },
        }
        self.log = self.repo / "projects/runtime/_architectural_orchestration_jobs/test/workflow.log"
        self.log.parent.mkdir(parents=True)
        self.log.write_text("ARCH\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_activation_metadata_required(self):
        project = dict(self.project)
        project["metadata"] = {}
        self.assertEqual(self.runtime._structural_bridge_tokens(project), [])

    def test_only_structural_tokens_are_bridged(self):
        self.assertEqual(
            self.runtime._structural_bridge_tokens(self.project),
            STRUCTURAL,
        )

    def test_success_requires_adapter_and_project_scoped_inp(self):
        def fake_run(*args, **kwargs):
            adapter = (
                self.repo
                / "projects/runtime"
                / self.job.project_id
                / "results/session_adapters/structural_engineering"
            )
            adapter.mkdir(parents=True)
            deck = adapter / "solver/calculix_LC-G.inp"
            deck.parent.mkdir(parents=True)
            deck.write_text("*HEADING\n", encoding="utf-8")
            return SimpleNamespace(returncode=0)

        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            side_effect=fake_run,
        ):
            result = self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["project_scoped_inp"]), 1)

    def test_runner_zero_without_inp_is_failure(self):
        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            return_value=SimpleNamespace(returncode=0),
        ):
            result = self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        self.assertFalse(result["passed"])

    def test_nonzero_runner_is_failure(self):
        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            return_value=SimpleNamespace(returncode=9),
        ):
            result = self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        self.assertFalse(result["passed"])

    def test_bridge_session_uses_same_project_id_and_structural_scope_only(self):
        def fake_run(*args, **kwargs):
            return SimpleNamespace(returncode=5)

        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            side_effect=fake_run,
        ):
            self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        session = json.loads(
            (
                self.log.parent
                / "structural_session_bridge/session.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(session["selected_project"], self.job.project_id)
        self.assertEqual(session["desired_outputs"], STRUCTURAL)
        self.assertNotIn("planning", session["desired_outputs"])

    def test_release_locks_preserved_in_bridge_evidence(self):
        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            return_value=SimpleNamespace(returncode=4),
        ):
            self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        session = json.loads(
            (
                self.log.parent
                / "structural_session_bridge/session.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(session["bridge"]["production_release"], "LOCKED")
        self.assertEqual(session["bridge"]["for_construction"], "LOCKED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
