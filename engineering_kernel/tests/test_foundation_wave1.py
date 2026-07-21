from __future__ import annotations

from engineering_kernel.tests.numeric_assertions import assert_float_close, assert_numeric_sequence_close
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.foundation import *


class FoundationWave1Tests(unittest.TestCase):
    def test_dataclass(self):
        foundation = RectangularFoundation(2.0, 3.0, 0.5)
        assert_float_close(self, foundation.area_m2, 6.0)
        assert_float_close(self, foundation.volume_m3, 3.0)

    def test_geometry_and_weight(self):
        assert_float_close(self, foundation_area(2.0, 3.0), 6.0)
        assert_float_close(self, foundation_volume(2.0, 3.0, 0.5), 3.0)
        assert_float_close(self, foundation_self_weight(2.0, 3.0, 0.5, 24.0), 72.0)

    def test_pressures(self):
        assert_float_close(self, average_contact_pressure(600.0, 6.0), 100.0)
        assert_float_close(self, net_foundation_pressure(120.0, 20.0), 100.0)

    def test_eccentricity_and_kern(self):
        assert_float_close(self, eccentricity(60.0, 600.0), 0.1)
        self.assertAlmostEqual(kern_limit(1.2), 0.2)
        self.assertTrue(within_kern(0.1, 1.2))
        self.assertFalse(within_kern(0.3, 1.2))

    def test_base_pressures(self):
        q_min, q_max = rectangular_base_pressures(600.0, 2.0, 3.0, 60.0)
        self.assertAlmostEqual(q_min, 70.0)
        self.assertAlmostEqual(q_max, 130.0)

    def test_effective_width(self):
        assert_float_close(self, effective_width(2.0, 0.2), 1.6)

    def test_bearing(self):
        assert_float_close(self, allowable_vertical_load(150.0, 4.0), 600.0)
        assert_float_close(self, bearing_utilization(120.0, 150.0), 0.8)
        assert_float_close(self, bearing_safety_factor(300.0, 100.0), 3.0)

    def test_stability(self):
        assert_float_close(self, sliding_resistance(100.0, 0.5, 10.0), 60.0)
        assert_float_close(self, sliding_safety_factor(100.0, 0.5, 30.0, 10.0), 2.0)
        assert_float_close(self, overturning_safety_factor(200.0, 100.0), 2.0)

    def test_settlement(self):
        self.assertAlmostEqual(one_dimensional_settlement(100.0, 10000.0, 2.0), 0.02, places=12)
        self.assertAlmostEqual(total_settlement([0.01, 0.02]), 0.03, places=12)
        self.assertAlmostEqual(differential_settlement(0.01, 0.03), 0.02, places=12)
        self.assertAlmostEqual(angular_distortion(0.01, 0.03, 10.0), 0.002, places=12)
        self.assertAlmostEqual(settlement_utilization(0.02, 0.04), 0.5, places=12)

    def test_strip_foundation(self):
        assert_float_close(self, strip_footing_line_load(100.0, 20.0), 120.0)
        assert_float_close(self, required_strip_width(120.0, 150.0), 0.8)

    def test_foundation_beam(self):
        left, right = simple_beam_reactions(4.0, 100.0, 1.0)
        assert_float_close(self, left, 75.0)
        assert_float_close(self, right, 25.0)
        assert_float_close(self, simply_supported_udl_max_moment(10.0, 4.0), 20.0)
        assert_float_close(self, simply_supported_udl_max_shear(10.0, 4.0), 20.0)

    def test_piles(self):
        assert_float_close(self, pile_group_capacity(100.0, 4, 0.8), 320.0)
        assert_float_close(self, average_pile_load(400.0, 4), 100.0)
        assert_float_close(self, pile_group_utilization(320.0, 100.0, 4, 0.8), 1.0)
        assert_numeric_sequence_close(self, distribute_load_equally(300.0, 3), (100.0, 100.0, 100.0))
        assert_float_close(self, load_uniformity_ratio([100.0, 100.0, 100.0]), 0.0)

    def test_invalid(self):
        with self.assertRaises(FoundationError):
            effective_width(1.0, 0.5)
        with self.assertRaises(FoundationError):
            pile_group_capacity(100.0, 0)
        with self.assertRaises(FoundationError):
            simple_beam_reactions(4.0, 10.0, 5.0)


if __name__ == "__main__":
    unittest.main()
