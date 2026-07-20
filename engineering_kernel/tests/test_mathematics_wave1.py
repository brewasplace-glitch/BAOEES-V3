from __future__ import annotations

import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.mathematics import (
    MathematicsError,
    add,
    arithmetic_mean,
    clamp,
    divide,
    dot_product,
    is_close,
    linear_interpolate,
    margin,
    normalize,
    percentage,
    percentage_change,
    power,
    round_to_increment,
    square_root,
    utilization,
    vector_magnitude,
    vector_normalize,
    weighted_mean,
)


class MathematicsWave1Tests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_divide(self):
        self.assertEqual(divide(9, 3), 3)

    def test_division_by_zero(self):
        with self.assertRaises(MathematicsError):
            divide(1, 0)

    def test_power(self):
        self.assertEqual(power(3, 2), 9)

    def test_square_root_negative_rejected(self):
        with self.assertRaises(MathematicsError):
            square_root(-1)

    def test_clamp(self):
        self.assertEqual(clamp(12, 0, 10), 10)

    def test_mean(self):
        self.assertAlmostEqual(arithmetic_mean([1, 2, 3, 4]), 2.5)

    def test_weighted_mean(self):
        self.assertAlmostEqual(weighted_mean([10, 20], [1, 3]), 17.5)

    def test_percentage(self):
        self.assertAlmostEqual(percentage(25, 200), 12.5)

    def test_percentage_change(self):
        self.assertAlmostEqual(percentage_change(100, 125), 25.0)

    def test_margin(self):
        self.assertEqual(margin(75, 100), 25)

    def test_utilization(self):
        self.assertAlmostEqual(utilization(80, 100), 0.8)

    def test_is_close(self):
        self.assertTrue(is_close(1.0, 1.0 + 1e-10))

    def test_round_to_increment(self):
        self.assertAlmostEqual(round_to_increment(1.24, 0.1), 1.2)

    def test_normalize(self):
        self.assertAlmostEqual(normalize(5, 0, 10), 0.5)

    def test_interpolate(self):
        self.assertAlmostEqual(linear_interpolate(5, 0, 0, 10, 100), 50)

    def test_dot_product(self):
        self.assertAlmostEqual(dot_product([1, 2, 3], [4, 5, 6]), 32)

    def test_vector_magnitude(self):
        self.assertAlmostEqual(vector_magnitude([3, 4]), 5)

    def test_vector_normalize(self):
        result = vector_normalize([3, 4])
        self.assertAlmostEqual(result[0], 0.6)
        self.assertAlmostEqual(result[1], 0.8)

    def test_non_finite_rejected(self):
        with self.assertRaises(MathematicsError):
            add(float("nan"), 1)


if __name__ == "__main__":
    unittest.main()
