import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.minimum_deliverable_baseline import evaluate_and_write_baseline
from phoenix.autonomy.suriname_structural_knowledge import is_suriname_building_context


class SurinameBaselineTests(unittest.TestCase):
    def _repo(self, td):
        repo = Path(td)
        (repo / "configs/phoenix").mkdir(parents=True)
        src = Path(__file__).resolve().parents[2] / "configs/phoenix"
        for name in (
            "suriname_structural_knowledge_policy_v1_0.json",
            "suriname_structural_reference_evidence_catalog_v1_0.json",
            "building_minimum_deliverable_baseline_v1_0.json",
        ):
            (repo / "configs/phoenix" / name).write_text((src / name).read_text(encoding="utf-8"), encoding="utf-8")
        return repo

    def test_suriname_building_context(self):
        self.assertTrue(is_suriname_building_context({
            "project_type": "BOUW",
            "project_context": {"geography": {"country_code": "SR"}},
        }))

    def test_reference_values_are_not_global_defaults(self):
        cfg = json.loads((Path(__file__).resolve().parents[2] / "configs/phoenix/suriname_structural_knowledge_policy_v1_0.json").read_text(encoding="utf-8"))
        layers = {x["id"]: x for x in cfg["knowledge_layers"]}
        self.assertFalse(layers["PROJECT_SPECIFIC_VALUES"]["may_be_reused_as_default"])

    def test_missing_manifest_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td)
            ws = repo / "projects/runtime/P1"
            ws.mkdir(parents=True)
            ctx = {
                "repository": str(repo),
                "workspace": str(ws),
                "project_id": "P1",
                "project_type": "BOUW",
                "project_context": {"geography": {"country_code": "SR"}},
            }
            result = evaluate_and_write_baseline(ctx)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertGreater(result["blocker_count"], 0)
            self.assertEqual(result["production_release"], "LOCKED")

    def test_not_applicable_requires_reason(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td)
            ws = repo / "projects/runtime/P2"
            (ws / "orchestration").mkdir(parents=True)
            (ws / "orchestration/minimum_deliverable_manifest.json").write_text(json.dumps({
                "items": [{"id": "B13_HVAC_PLAN", "status": "NOT_APPLICABLE_WITH_REASON"}]
            }), encoding="utf-8")
            ctx = {
                "repository": str(repo),
                "workspace": str(ws),
                "project_id": "P2",
                "project_type": "BOUW",
                "project_context": {"geography": {"country_code": "SR"}},
            }
            result = evaluate_and_write_baseline(ctx)
            hvac = next(x for x in result["items"] if x["id"] == "B13_HVAC_PLAN")
            self.assertEqual(hvac["status"], "BLOCKED_WITH_EXPLICIT_REASON")
            self.assertEqual(hvac["reason"], "NOT_APPLICABLE_REASON_REQUIRED")

    def test_generated_validated_requires_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td)
            ws = repo / "projects/runtime/P3"
            (ws / "orchestration").mkdir(parents=True)
            (ws / "orchestration/minimum_deliverable_manifest.json").write_text(json.dumps({
                "items": [{"id": "B01_FLOOR_PLAN", "status": "GENERATED_AND_VALIDATED"}]
            }), encoding="utf-8")
            ctx = {
                "repository": str(repo),
                "workspace": str(ws),
                "project_id": "P3",
                "project_type": "BOUW",
                "project_context": {"geography": {"country_code": "SR"}},
            }
            result = evaluate_and_write_baseline(ctx)
            floor = next(x for x in result["items"] if x["id"] == "B01_FLOOR_PLAN")
            self.assertEqual(floor["reason"], "VALIDATED_EVIDENCE_REFERENCE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
