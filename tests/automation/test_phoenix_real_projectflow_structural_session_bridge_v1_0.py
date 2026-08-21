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


def _canonical_fixture(project_id: str) -> dict:
    return {
        "schema_version": "phoenix.architectural-model/4.0.0",
        "project_id": project_id + "-VAR-E",
        "project_name": "Bridge regression fixture",
        "levels": [
            {
                "id": "L00",
                "name": "Ground",
                "elevation_m": 0.0,
                "floor_to_floor_m": 3.3,
            }
        ],
        "walls": [
            {
                "id": "W1",
                "level_id": "L00",
                "start": [0.0, 0.0],
                "end": [10.0, 0.0],
                "height_m": 3.3,
                "thickness_m": 0.30,
                "external": True,
            }
        ],
        "spaces": [
            {
                "id": "S1",
                "level_id": "L00",
                "name": "Assembly",
                "polygon": [
                    [0.0, 0.0],
                    [10.0, 0.0],
                    [10.0, 7.0],
                    [0.0, 7.0],
                    [0.0, 0.0],
                ],
            }
        ],
        "openings": [
            {
                "id": "D1",
                "kind": "door",
                "wall_id": "W1",
                "width_m": 1.2,
                "height_m": 2.3,
            }
        ],
        "stairs": [],
        "candidate_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }


class StructuralSessionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name).resolve()
        (self.repo / "projects/runtime").mkdir(parents=True)
        (self.repo / "configs/phoenix").mkdir(parents=True)
        (self.repo / "runners").mkdir(parents=True)

        runner_names = {
            "architecture": "runners/generic_architecture.py",
            "digital_twin": "runners/generic_digital_twin.py",
            "structural_engineering": "runners/generic_structural.py",
        }
        for rel in runner_names.values():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("raise SystemExit(0)\n", encoding="utf-8")

        config = {
            "output_capability_map": {
                token: ["structural_engineering"] for token in STRUCTURAL
            },
            "capabilities": {
                "project_bootstrap": {
                    "label": "Project bootstrap",
                    "execution_mode": "internal",
                    "depends_on": [],
                },
                "intake_normalization": {
                    "label": "Intake normalization",
                    "execution_mode": "internal",
                    "depends_on": ["project_bootstrap"],
                },
                "architecture": {
                    "label": "Architecture",
                    "execution_mode": "adapter",
                    "session_adapter_ready": True,
                    "depends_on": ["intake_normalization"],
                    "runner_candidates": [runner_names["architecture"]],
                },
                "digital_twin": {
                    "label": "Digital Twin",
                    "execution_mode": "adapter",
                    "session_adapter_ready": True,
                    "depends_on": ["architecture"],
                    "runner_candidates": [runner_names["digital_twin"]],
                },
                "structural_engineering": {
                    "label": "Structural Engineering",
                    "execution_mode": "adapter",
                    "session_adapter_ready": True,
                    "depends_on": ["architecture", "digital_twin"],
                    "runner_candidates": [runner_names["structural_engineering"]],
                },
                "cost_planning": {
                    "label": "Cost planning",
                    "execution_mode": "internal",
                    "depends_on": ["project_bootstrap"],
                },
            },
            "capability_order": [
                "project_bootstrap",
                "intake_normalization",
                "architecture",
                "digital_twin",
                "structural_engineering",
                "cost_planning",
            ],
        }
        config["output_capability_map"]["planning"] = ["cost_planning"]
        (
            self.repo
            / "configs/phoenix/autonomous_project_orchestrator_v1_0.json"
        ).write_text(json.dumps(config), encoding="utf-8")

        (
            self.repo
            / "runners/PROJECT_PHOENIX_autonomous_session_orchestrator_v1_0_0.py"
        ).write_text("print('fake')\n", encoding="utf-8")

        self.runtime = ArchitecturalOrchestrationRuntime(self.repo)
        self.job = ArchitecturalOrchestrationJob(
            job_id="bridge-test",
            project_file="configs/projects/test.json",
            project_id="MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            status="RUNNING",
            started_at="2026-08-21T00:00:00+00:00",
            output_dir="projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            log_path=(
                "projects/runtime/_architectural_orchestration_jobs/test/workflow.log"
            ),
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

        self.project_runtime = (
            self.repo / "projects/runtime" / self.job.project_id
        )
        delivery = (
            self.project_runtime
            / "delivery"
            / "nonresidential_reuse_v1"
        )
        variant = delivery / "variants" / "variant_E"
        variant.mkdir(parents=True, exist_ok=True)
        (delivery / "delivery_manifest.json").write_text(
            json.dumps(
                {
                    "schema": "PHOENIX_GENERIC_NONRESIDENTIAL_REAL_PROJECT_AE_DELIVERY_v1",
                    "project_id": self.job.project_id,
                    "engine_route": "NONRESIDENTIAL_REUSE_V1",
                    "recommended_variant_id": "E",
                    "governance": {
                        "production_locked": True,
                        "for_construction_locked": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        (variant / "canonical_architectural_model.json").write_text(
            json.dumps(_canonical_fixture(self.job.project_id)),
            encoding="utf-8",
        )

        self.log = (
            self.repo
            / "projects/runtime/_architectural_orchestration_jobs/test/workflow.log"
        )
        self.log.parent.mkdir(parents=True)
        self.log.write_text("ARCH\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _isolated_structural_dir(self) -> Path:
        return (
            self.log.parent
            / "structural_session_bridge"
            / "workspace"
            / "results"
            / "session_adapters"
            / "structural_engineering"
        )

    def _write_isolated_inp(self) -> Path:
        adapter = self._isolated_structural_dir()
        adapter.mkdir(parents=True, exist_ok=True)
        deck = adapter / "solver/calculix_LC-G.inp"
        deck.parent.mkdir(parents=True, exist_ok=True)
        deck.write_text("*HEADING\n", encoding="utf-8")
        return deck

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
            self._write_isolated_inp()
            return SimpleNamespace(returncode=0)

        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            side_effect=fake_run,
        ):
            result = self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )

        self.assertTrue(result["passed"])
        self.assertEqual(len(result["isolated_project_scoped_inp"]), 1)
        self.assertEqual(len(result["project_scoped_inp"]), 1)
        published = (
            self.project_runtime
            / "results/session_adapters/structural_engineering"
        )
        self.assertTrue(published.is_dir())

    def test_runner_zero_without_inp_is_failure(self):
        with mock.patch(
            "phoenix.local_app.architectural_orchestration_runtime.subprocess.run",
            return_value=SimpleNamespace(returncode=0),
        ):
            result = self.runtime._run_structural_capability_bridge(
                self.job, self.project, self.log
            )
        self.assertFalse(result["passed"])
        self.assertFalse(result["published"])

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
        self.assertIn("upload_batch", session)
        self.assertTrue(session["bootstrap"]["workspace"].endswith(
            "structural_session_bridge/workspace"
        ))
        self.assertFalse(
            session["bridge"]["primary_ae_workspace_overwrite"]
        )

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
