import json
import tempfile
import unittest
from pathlib import Path

from phoenix.adapters.permit_compliance_adapter import run_permit_compliance
from phoenix.permit_compliance import (
    ComplianceRule,
    PermitComplianceEngine,
    PermitComplianceError,
    PermitProjectContext,
)


class Wave158Tests(unittest.TestCase):
    def setUp(self):
        self.engine = PermitComplianceEngine()
        self.context = PermitProjectContext(
            project_id="PHX",
            jurisdiction="NL",
            permit_type="building",
            digital_twin_revision=7,
        )

    def test_all_rules_pass_but_human_review_required(self):
        result = self.engine.evaluate(
            context=self.context,
            digital_twin={"project": {"name": "Phoenix"}},
            rules=(ComplianceRule("R1", "Name", "project.name", "not_empty"),),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(result["permit_status"], "review_required")
        self.assertEqual(result["completeness"]["score_percent"], 100.0)

    def test_ready_without_human_approval(self):
        context = PermitProjectContext("PHX", "NL", "building", 7, False)
        result = self.engine.evaluate(
            context=context,
            digital_twin={"project": {"name": "Phoenix"}},
            rules=(ComplianceRule("R1", "Name", "project.name", "not_empty"),),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(result["permit_status"], "ready_for_submission")

    def test_blocking_failure(self):
        result = self.engine.evaluate(
            context=self.context,
            digital_twin={"building": {"height": 12}},
            rules=(ComplianceRule("R1", "Height", "building.height", "lte", 10, "error"),),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(result["permit_status"], "blocked")
        self.assertEqual(result["completeness"]["blocking_findings"], 1)

    def test_warning_requires_review(self):
        context = PermitProjectContext("PHX", "NL", "building", 7, False)
        result = self.engine.evaluate(
            context=context,
            digital_twin={},
            rules=(ComplianceRule("R1", "Optional metadata", "meta.note", "exists", severity="warning"),),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(result["permit_status"], "review_required")

    def test_duplicate_rule_rejected(self):
        rule = ComplianceRule("R1", "Name", "project.name", "exists")
        with self.assertRaisesRegex(PermitComplianceError, "Duplicate"):
            self.engine.evaluate(
                context=self.context,
                digital_twin={},
                rules=(rule, rule),
                rule_set_id="base",
                rule_set_version="1.0",
            )

    def test_nested_path_and_in_operator(self):
        result = self.engine.evaluate(
            context=self.context,
            digital_twin={"project": {"use": "assembly"}},
            rules=(ComplianceRule("R1", "Use", "project.use", "in", ["assembly", "office"]),),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(result["findings"][0]["status"], "passed")

    def test_evidence_hashes(self):
        result = self.engine.evaluate(
            context=self.context,
            digital_twin={},
            rules=(),
            rule_set_id="base",
            rule_set_version="1.0",
        )
        self.assertEqual(len(result["evidence"]["result_sha256"]), 64)

    def test_adapter_writes_output(self):
        request = {
            "context": {
                "project_id": "PHX",
                "jurisdiction": "NL",
                "permit_type": "building",
                "digital_twin_revision": 7,
            },
            "digital_twin": {"project": {"name": "Phoenix"}},
            "rule_set_id": "base",
            "rule_set_version": "1.0",
            "rules": [
                {
                    "rule_id": "R1",
                    "title": "Name",
                    "path": "project.name",
                    "operator": "not_empty",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            result = run_permit_compliance(request, path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result["adapter"]["version"], "1.0.0")
        self.assertEqual(stored["permit_status"], "review_required")

    def test_write_result_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            self.engine.write_result(
                context=self.context,
                digital_twin={},
                rules=(),
                rule_set_id="base",
                rule_set_version="1.0",
                destination=path,
            )
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
