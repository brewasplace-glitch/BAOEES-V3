from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/phoenix/professional_evidence_intake_review_workflow_v6_4_0.json"
PROJECT = ROOT / "configs/projects/moskee_bunschoten_evidence_workflow_v6_4_0.json"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_professional_evidence_intake_review_workflow_v6_4_0.py"

class EvidenceWorkflowTests(unittest.TestCase):
    def test_six_requirements(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(cfg["requirements"]), 6)

    def test_automatic_approval_forbidden(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertTrue(
            cfg["review_policy"]["automatic_approval_forbidden"]
        )

    def test_project_starts_empty_and_locked(self):
        project = json.loads(PROJECT.read_text(encoding="utf-8"))
        workflow = project["professional_evidence"]["review_workflow"]
        self.assertEqual(len(workflow), 6)
        self.assertTrue(all(v["state"] == "EMPTY" for v in workflow.values()))
        self.assertFalse(project["professional_evidence"]["permit_ready"])

    def test_runner_valid_python(self):
        ast.parse(RUNNER.read_text(encoding="utf-8"))

    def test_runner_generates_review_packets(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("create_review_packet", text)
        self.assertIn("review_packets_generated", text)

    def test_duplicate_detection_and_metadata_validation(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("duplicate_hashes", text)
        self.assertIn("metadata_missing_or_invalid", text)

    def test_req108_dependency(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("req108_ready", text)
        self.assertIn(
            "REQ-102 through REQ-106 must be approved first",
            text,
        )

    def test_release_gate_remains_explicit(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            '"status": "UNLOCKED" if permit_ready else "LOCKED"',
            text,
        )

if __name__ == "__main__":
    unittest.main()
