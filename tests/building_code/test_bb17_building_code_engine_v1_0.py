from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.building_code import BuildingCodeEngine, CodeProfileRegistry, RuleResultStatus
from phoenix.building_code.safe_eval import SafeExpressionEvaluator, UnsafeRuleExpression

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "configs" / "phoenix" / "building_code_profiles" / "phoenix_building_model_integrity_v1_0.json"


def valid_model() -> dict:
    return {
        "schema_version": "phoenix.building-model/1.0",
        "project_id": "PHX-TEST-001",
        "name": "BB17 test model",
        "units": "SI",
        "levels": [{"id":"LVL-00","name":"Ground floor","elevation_m":0.0,"height_m":3.2,"metadata":{}}],
        "spaces": [{"id":"SPC-001","name":"Room","level_id":"LVL-00","area_m2":24.0,"volume_m3":76.8,"usage":"test","metadata":{}}],
        "elements": [{"id":"ELM-WALL-001","name":"Wall","category":"wall","level_id":"LVL-00","geometry":{"length_m":6.0},"material":{"name":"masonry"},"properties":{},"source_refs":[]}],
        "relationships": [{"type":"contains","source_id":"LVL-00","target_id":"SPC-001","metadata":{}}],
        "metadata": {},
    }


class BuildingCodeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CodeProfileRegistry()
        self.profile = self.registry.load_file(PROFILE)
        self.engine = BuildingCodeEngine()

    def test_valid_model_passes_all_baseline_rules(self) -> None:
        report = self.engine.evaluate(valid_model(), self.profile)
        self.assertTrue(report.is_compliant_for(self.profile.fail_severities))
        self.assertEqual(11, report.summary["pass"])

    def test_bad_space_reference_fails_with_evidence(self) -> None:
        model = valid_model()
        model["spaces"][0]["level_id"] = "LVL-UNKNOWN"
        report = self.engine.evaluate(model, self.profile)
        result = next(item for item in report.evaluations if item.rule_id == "PHX-BMI-006")
        self.assertEqual(RuleResultStatus.FAIL, result.status)
        self.assertTrue(result.evidence)
        self.assertFalse(report.is_compliant_for(self.profile.fail_severities))

    def test_unsafe_expression_is_rejected(self) -> None:
        with self.assertRaises(UnsafeRuleExpression):
            SafeExpressionEvaluator(valid_model()).evaluate('__import__("os").system("x")')

    def test_duplicate_rule_ids_are_rejected(self) -> None:
        data = json.loads(PROFILE.read_text(encoding="utf-8"))
        data["rules"].append(dict(data["rules"][0]))
        with self.assertRaises(ValueError):
            self.registry.load_dict(data)

    def test_report_fingerprint_is_deterministic(self) -> None:
        a = self.engine.evaluate(valid_model(), self.profile)
        b = self.engine.evaluate(valid_model(), self.profile)
        self.assertEqual(self.engine.fingerprint_report(a, self.profile), self.engine.fingerprint_report(b, self.profile))

    def test_bb16_style_object_is_supported(self) -> None:
        class ModelObject:
            def to_dict(self) -> dict:
                return valid_model()
        report = self.engine.evaluate(ModelObject(), self.profile)
        self.assertTrue(report.is_compliant_for(self.profile.fail_severities))

    def test_export_contains_compliance_and_fingerprint(self) -> None:
        report = self.engine.evaluate(valid_model(), self.profile)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.engine.export_report(report, self.profile, Path(tmp) / "report.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["compliant"])
        self.assertIn("report_fingerprint_sha256", data)


if __name__ == "__main__":
    unittest.main()
