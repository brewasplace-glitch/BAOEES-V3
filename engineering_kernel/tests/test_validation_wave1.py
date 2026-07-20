from __future__ import annotations
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.validation import *


class ValidationWave1Tests(unittest.TestCase):
    def test_basic_validators(self):
        self.assertTrue(validate_type(1, int))
        self.assertTrue(validate_required("x"))
        self.assertFalse(validate_required(" "))
        self.assertTrue(validate_not_nan(1.0))
        self.assertFalse(validate_not_nan(float("nan")))
        self.assertTrue(validate_finite(2.0))
        self.assertFalse(validate_finite(float("inf")))

    def test_ranges(self):
        self.assertTrue(validate_range(5, 0, 10))
        self.assertFalse(validate_range(10, 0, 10, inclusive=False))
        self.assertTrue(validate_positive(1))
        self.assertFalse(validate_positive(0))
        self.assertTrue(validate_non_negative(0))

    def test_choice_length_dimensions_units(self):
        self.assertTrue(validate_choice("A", ["A", "B"]))
        self.assertTrue(validate_length([1, 2], 1, 3))
        self.assertTrue(validate_dimensions((2, 3), (2, 3)))
        self.assertTrue(validate_units("kN", ["N", "kN"]))

    def test_consistency_and_monotonic(self):
        self.assertTrue(validate_consistency([1, 1, 1]))
        self.assertFalse(validate_consistency([1, 2]))
        self.assertTrue(validate_monotonic([1, 1, 2]))
        self.assertFalse(validate_monotonic([1, 1, 2], strictly=True))

    def test_tolerances(self):
        self.assertTrue(validate_tolerance(1.001, 1.0, 0.01))
        self.assertTrue(validate_relative_tolerance(100.1, 100.0, 0.01))
        self.assertTrue(validate_rounding(1.23, 2))
        self.assertFalse(validate_rounding(1.234, 2))
        self.assertTrue(validate_convergence(10.0, 10.001, 0.01))

    def test_engineering_validators(self):
        self.assertTrue(validate_factor_of_safety(150, 100, 1.5))
        self.assertTrue(validate_utilization(0.95))
        self.assertTrue(validate_material_property(30, 20, 40))
        self.assertTrue(validate_geometry_non_degenerate(0.1))
        self.assertTrue(validate_load_magnitude(-10))
        self.assertFalse(validate_load_magnitude(-10, allow_negative=False))

    def test_dependency_traceability_registry(self):
        self.assertTrue(validate_dependency_set(["A"], ["A", "B"]))
        self.assertTrue(validate_traceability(["F1"], ["F1", "F2"]))
        self.assertTrue(validate_registry_unique_ids([{"id": "A"}, {"id": "B"}]))
        self.assertFalse(validate_registry_unique_ids([{"id": "A"}, {"id": "A"}]))

    def test_issues_and_reports(self):
        warning = create_issue("W1", "warning", "warn")
        error = create_issue("E1", "error", "error")
        self.assertEqual(classify_issue("fatal"), "CRITICAL")
        report = create_validation_report("R1", [warning, error], {"source": "test"})
        self.assertFalse(report.passed)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.warning_count, 1)
        summary = validation_summary(report)
        self.assertEqual(summary["issue_count"], 2)
        self.assertEqual(summary["counts"]["WARNING"], 1)

    def test_merge_reports(self):
        a = create_validation_report("A", [create_issue("I", "info", "info")])
        b = create_validation_report("B", [create_issue("W", "warn", "warning")])
        merged = merge_validation_reports("Merged", [a, b])
        self.assertEqual(len(merged.issues), 2)
        self.assertEqual(merged.metadata["merged_report_count"], 2)

    def test_invalid_tolerance(self):
        with self.assertRaises(ValidationError):
            validate_tolerance(1, 1, -1)

    def test_invalid_range_definition(self):
        with self.assertRaises(ValidationError):
            validate_range(5, 10, 0)

    def test_invalid_severity(self):
        with self.assertRaises(ValidationError):
            classify_issue("unknown")


if __name__ == "__main__":
    unittest.main()
