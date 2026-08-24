import json
from pathlib import Path
import tempfile
import unittest

from phoenix.autonomy.generated_input_validation_list_v1_0 import (
    CLASSIFICATIONS,
    ValidationListError,
    build_validation_list,
    infer_classification,
    normalize_input_records,
    write_validation_list,
)


class GeneratedInputValidationListTests(unittest.TestCase):
    def test_explicit_classification_is_preserved(self):
        self.assertEqual(
            infer_classification({"classification": "AUTO_DERIVED"}),
            "AUTO_DERIVED",
        )

    def test_invalid_explicit_classification_fails_closed(self):
        with self.assertRaises(ValidationListError):
            infer_classification({"classification": "VERIFIED_BY_MAGIC"})

    def test_source_backed_candidate_is_inferred(self):
        self.assertEqual(
            infer_classification({"source_record_id": "SRC-001"}),
            "SOURCE_BACKED_CANDIDATE",
        )

    def test_assumption_candidate_is_inferred_without_source(self):
        self.assertEqual(
            infer_classification({"field": "x", "value": 1}),
            "ASSUMED_CANDIDATE",
        )

    def test_professional_review_required_has_priority(self):
        self.assertEqual(
            infer_classification({"professional_review_required": True}),
            "PROFESSIONAL_REVIEW_REQUIRED",
        )

    def test_human_required_is_supported(self):
        self.assertEqual(
            infer_classification({"human_required": True}),
            "HUMAN_REQUIRED",
        )

    def test_common_container_is_normalized(self):
        payload = {"assumptions": [{"field": "soil", "value": "clay"}]}
        records = normalize_input_records(payload)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["_container"], "assumptions")

    def test_field_ids_are_deterministic(self):
        payload = [{"field": "height", "value": 3.0, "derived": True}]
        a = build_validation_list(payload, project_id="P1", package_id="PKG")
        b = build_validation_list(payload, project_id="P1", package_id="PKG")
        self.assertEqual(
            a["items"][0]["phoenix_field_id"],
            b["items"][0]["phoenix_field_id"],
        )

    def test_source_confidence_and_reason_are_preserved(self):
        payload = [{
            "field": "groundwater",
            "value": -0.5,
            "source": "GeoTwin",
            "confidence": "MEDIUM",
            "reason": "candidate",
        }]
        result = build_validation_list(payload)
        item = result["items"][0]
        self.assertEqual(item["source"], "GeoTwin")
        self.assertEqual(item["confidence"], "MEDIUM")
        self.assertEqual(item["rationale"], "candidate")

    def test_summary_counts_all_classifications(self):
        payload = [
            {"field": "a", "value": 1, "derived": True},
            {"field": "b", "value": 2, "source": "SRC"},
            {"field": "c", "value": 3},
            {"field": "d", "value": 4, "human_required": True},
            {"field": "e", "value": 5, "professional_review_required": True},
        ]
        result = build_validation_list(payload)
        counts = result["summary"]["classification_counts"]
        self.assertEqual(result["summary"]["total_items"], 5)
        for name in CLASSIFICATIONS:
            self.assertEqual(counts[name], 1)

    def test_review_contract_is_not_auto_approved(self):
        result = build_validation_list([{"field": "x", "value": 1}])
        item = result["items"][0]
        self.assertEqual(item["review"]["status"], "AWAITING_VALIDATION")
        self.assertIsNone(item["review"]["reviewer_action"])
        self.assertTrue(result["safety"]["concept_only_until_review"])
        self.assertFalse(result["safety"]["automatic_approval"])

    def test_write_validation_list_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "validation.json"
            result = write_validation_list(
                target,
                [{"field": "x", "value": 1, "derived": True}],
                project_id="PAT",
            )
            loaded = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], result["schema_version"])
            self.assertEqual(loaded["items"][0]["field"], "x")


if __name__ == "__main__":
    unittest.main()
