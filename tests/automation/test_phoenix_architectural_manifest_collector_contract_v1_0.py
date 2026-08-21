from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from phoenix.local_app.architectural_orchestration_runtime import (
    ArchitecturalOrchestrationJob,
    ArchitecturalOrchestrationRuntime,
)

class ArchitecturalManifestCollectorContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name).resolve()
        (self.repo / "projects/runtime").mkdir(parents=True)
        self.runtime = ArchitecturalOrchestrationRuntime(self.repo)
        self.job = ArchitecturalOrchestrationJob(
            job_id="job-test",
            project_file="configs/projects/test.json",
            project_id="MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            status="RUNNING",
            started_at="2026-08-21T00:00:00+00:00",
            output_dir="projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001",
            log_path="projects/runtime/_architectural_orchestration_jobs/test/workflow.log",
            command=["python", "-m", "example"],
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_nonresidential_route_maps_to_nonresidential_delivery(self):
        project = {
            "metadata": {
                "phoenix_architectural_engine_route": {
                    "route": "NONRESIDENTIAL_REUSE_V1"
                }
            }
        }
        path = self.runtime._planned_delivery_manifest(self.job.project_id, project)
        self.assertEqual(
            path,
            self.repo / "projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001/delivery/nonresidential_reuse_v1/delivery_manifest.json",
        )

    def test_legacy_route_preserves_architectural_ae_folder(self):
        path = self.runtime._planned_delivery_manifest(self.job.project_id, {})
        self.assertEqual(
            path,
            self.repo / "projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001/delivery/architectural_ae_v1_0/delivery_manifest.json",
        )

    def test_absolute_cli_manifest_path_is_collected(self):
        manifest = (
            self.repo
            / "projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001/delivery/nonresidential_reuse_v1/delivery_manifest.json"
        )
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{"recommended_variant_id":"E"}\n', encoding="utf-8")
        log = self.repo / "workflow.log"
        payload = {
            "project_id": self.job.project_id,
            "manifest_path": str(manifest),
            "recommended_variant_id": "E",
        }
        log.write_text(
            "PROJECT PHOENIX ARCHITECTURAL A-E ORCHESTRATION\nCommand: []\n\n"
            + json.dumps(payload, indent=2)
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(self.runtime._result_manifest_from_log(self.job, log), manifest)

    def test_relative_cli_manifest_path_is_collected(self):
        rel = Path(
            "projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001/delivery/nonresidential_reuse_v1/delivery_manifest.json"
        )
        manifest = self.repo / rel
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{"recommended_variant_id":"E"}\n', encoding="utf-8")
        log = self.repo / "workflow.log"
        log.write_text(
            "header\n\n"
            + json.dumps({"project_id": self.job.project_id, "manifest_path": rel.as_posix()}),
            encoding="utf-8",
        )
        self.assertEqual(self.runtime._result_manifest_from_log(self.job, log), manifest)

    def test_result_contract_rejects_wrong_project_id(self):
        log = self.repo / "workflow.log"
        log.write_text(
            json.dumps(
                {
                    "project_id": "OTHER-PROJECT",
                    "manifest_path": str(
                        self.repo
                        / "projects/runtime/MOSKEE-BUNSCHOTEN-E2E-REAL-001/delivery/nonresidential_reuse_v1/delivery_manifest.json"
                    ),
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(RuntimeError):
            self.runtime._result_manifest_from_log(self.job, log)

    def test_result_contract_rejects_path_escape(self):
        outside = self.repo / "outside/delivery_manifest.json"
        log = self.repo / "workflow.log"
        log.write_text(
            json.dumps(
                {
                    "project_id": self.job.project_id,
                    "manifest_path": str(outside),
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(RuntimeError):
            self.runtime._result_manifest_from_log(self.job, log)

    def test_missing_result_contract_returns_none_for_legacy_fallback(self):
        log = self.repo / "workflow.log"
        log.write_text("PROJECT PHOENIX\nCommand: []\n\nlegacy output only\n", encoding="utf-8")
        self.assertIsNone(self.runtime._result_manifest_from_log(self.job, log))

if __name__ == "__main__":
    unittest.main(verbosity=2)
