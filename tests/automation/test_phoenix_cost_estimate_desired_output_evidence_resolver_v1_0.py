import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.desired_output_evidence import validate_desired_output_evidence


class CostEstimateDesiredOutputEvidenceTests(unittest.TestCase):
    def _repo(self):
        td = tempfile.TemporaryDirectory()
        repo = Path(td.name)
        workspace = repo / "projects" / "runtime" / "TEST"
        cost_dir = workspace / "results" / "session_adapters" / "cost_planning"
        cost_dir.mkdir(parents=True, exist_ok=True)
        return td, repo, workspace, cost_dir

    def test_safe_level_a_cost_estimate_is_accepted(self):
        td, repo, workspace, cost_dir = self._repo()
        try:
            artifact = cost_dir / "cost_estimate.json"
            artifact.write_text(json.dumps({
                "schema_version": "phoenix.level-a-cost-estimate-artifact/1.0",
                "artifact_type": "COST_ESTIMATE",
                "status": "PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES",
                "pricing_rules": {"price_fabricated": False},
                "professional_review_required": True,
                "automatic_professional_approval": False,
                "production_release": "LOCKED",
                "for_construction": "LOCKED"
            }), encoding="utf-8")
            ref = artifact.relative_to(repo).as_posix()
            result = validate_desired_output_evidence(
                repository=repo,
                workspace=workspace,
                output_id="cost_estimate",
                capability_states={"cost_planning": {"outputs": [ref], "status": "PASSED"}},
            )
            self.assertEqual(result["status"], "PASSED", result)
            self.assertIn(ref, result["evidence"])
        finally:
            td.cleanup()

    def test_fabricated_price_level_a_artifact_is_rejected(self):
        td, repo, workspace, cost_dir = self._repo()
        try:
            artifact = cost_dir / "cost_estimate.json"
            artifact.write_text(json.dumps({
                "schema_version": "phoenix.level-a-cost-estimate-artifact/1.0",
                "artifact_type": "COST_ESTIMATE",
                "pricing_rules": {"price_fabricated": True},
                "automatic_professional_approval": False,
                "production_release": "LOCKED"
            }), encoding="utf-8")
            ref = artifact.relative_to(repo).as_posix()
            result = validate_desired_output_evidence(
                repository=repo,
                workspace=workspace,
                output_id="cost_estimate",
                capability_states={"cost_planning": {"outputs": [ref], "status": "PASSED"}},
            )
            self.assertEqual(result["status"], "BLOCKED", result)
        finally:
            td.cleanup()

    def test_legacy_local_cost_calculation_remains_accepted(self):
        td, repo, workspace, cost_dir = self._repo()
        try:
            artifact = cost_dir / "local_cost_calculation.json"
            artifact.write_text('{"status":"PARTIAL_UNRESOLVED_PRICES"}', encoding="utf-8")
            ref = artifact.relative_to(repo).as_posix()
            result = validate_desired_output_evidence(
                repository=repo,
                workspace=workspace,
                output_id="cost_estimate",
                capability_states={"cost_planning": {"outputs": [ref], "status": "PASSED"}},
            )
            self.assertEqual(result["status"], "PASSED", result)
            self.assertIn(ref, result["evidence"])
        finally:
            td.cleanup()

    def test_unrelated_json_is_not_cost_estimate_evidence(self):
        td, repo, workspace, cost_dir = self._repo()
        try:
            artifact = cost_dir / "cost_planning_plan.json"
            artifact.write_text('{"status":"PASSED"}', encoding="utf-8")
            ref = artifact.relative_to(repo).as_posix()
            result = validate_desired_output_evidence(
                repository=repo,
                workspace=workspace,
                output_id="cost_estimate",
                capability_states={"cost_planning": {"outputs": [ref], "status": "PASSED"}},
            )
            self.assertEqual(result["status"], "BLOCKED", result)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
