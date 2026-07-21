from __future__ import annotations

import math
import unittest

from engineering_kernel.tests.numeric_assertions import (
    assert_float_close,
    assert_numeric_sequence_close,
)


class NumericAssertionsTests(unittest.TestCase):
    def test_binary_rounding_is_tolerated(self):
        assert_float_close(self, 0.1 + 0.2, 0.3)

    def test_engineering_scale_relative_tolerance(self):
        assert_float_close(self, 1_000_000.0005, 1_000_000.0)

    def test_small_values_use_absolute_tolerance(self):
        assert_float_close(self, 5e-13, 0.0)

    def test_material_difference_fails(self):
        with self.assertRaises(AssertionError):
            assert_float_close(self, 1.01, 1.0)

    def test_nan_fails(self):
        with self.assertRaises(AssertionError):
            assert_float_close(self, math.nan, math.nan)

    def test_sequences(self):
        assert_numeric_sequence_close(self, [0.1 + 0.2, 1.0], [0.3, 1.0])

    def test_boolean_rejected(self):
        with self.assertRaises(AssertionError):
            assert_float_close(self, True, 1.0)


if __name__ == "__main__":
    unittest.main()
