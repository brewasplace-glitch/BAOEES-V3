from __future__ import annotations
from engineering_kernel.tests.numeric_assertions import assert_float_close, assert_numeric_sequence_close
import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.loads import *


class LoadsWave1Tests(unittest.TestCase):
    def test_create_load(self):
        load = create_load("L1", "test", 10, (3, 0, 4))
        self.assertAlmostEqual(load.direction[0], 0.6)
        self.assertAlmostEqual(load.direction[2], 0.8)

    def test_factories(self):
        self.assertEqual(dead_load("G", 10).category, "dead")
        self.assertEqual(imposed_load("Q", 5).category, "imposed")
        self.assertEqual(wind_load("W", 3, (1, 0, 0)).category, "wind")
        self.assertEqual(snow_load("S", 2).category, "snow")
        self.assertEqual(seismic_load("E", 7, (1, 0, 0)).category, "seismic")
        self.assertEqual(thermal_load("T", 4, (1, 0, 0)).category, "thermal")

    def test_pressures(self):
        self.assertAlmostEqual(hydrostatic_pressure(1000, 9.81, 2), 19620)
        self.assertAlmostEqual(earth_pressure_unit_weight(18, 3, 0.33), 17.82)

    def test_load_transformations(self):
        self.assertEqual(uniform_line_load(5, 2), 10)
        self.assertEqual(uniform_area_load(100, 20), 5)
        self.assertEqual(point_load_from_pressure(4, 3), 12)
        self.assertEqual(resultant_of_uniform_line_load(8, 5), 40)
        self.assertEqual(resultant_of_uniform_area_load(6, 10), 60)

    def test_triangular_and_trapezoidal(self):
        self.assertEqual(triangular_line_load_resultant(10, 6), 30)
        self.assertEqual(triangular_line_load_position(6), 4)
        self.assertEqual(trapezoidal_line_load_resultant(4, 10, 3), 21)

    def test_moment(self):
        self.assertEqual(moment_from_force(10, 2.5), 25)

    def test_components_and_vector(self):
        load = create_load("X", "test", 10, (1, 0, 0))
        self.assertEqual(load_component(load, 0), 10)
        assert_numeric_sequence_close(self, load_vector(load), (10.0, 0.0, 0.0))

    def test_scale(self):
        load = dead_load("G", 10)
        scaled = scale_load(load, 1.5)
        self.assertEqual(scaled.magnitude, 15)

    def test_resultants(self):
        a = create_load("A", "test", 3, (1, 0, 0))
        b = create_load("B", "test", 4, (0, 1, 0))
        assert_numeric_sequence_close(self, sum_load_vectors([a, b]), (3.0, 4.0, 0.0))
        r = resultant_load([a, b])
        self.assertAlmostEqual(r.magnitude, 5)

    def test_combinations(self):
        g = dead_load("G", 10)
        q = imposed_load("Q", 5)
        terms = [LoadCombinationTerm(g, 1.35), LoadCombinationTerm(q, 1.5)]
        self.assertAlmostEqual(combination_value(terms), 21)
        vector = combination_vector(terms)
        self.assertAlmostEqual(vector[2], -21)
        self.assertEqual(characteristic_combination([g, q]), 15)
        self.assertEqual(design_combination([g, q], [1.35, 1.5]), 21)

    def test_accidental_combination(self):
        g = dead_load("G", 10)
        q = imposed_load("Q", 5)
        a = create_load("A", "accidental", 2, (1, 0, 0))
        assert_float_close(self, accidental_combination([g], [q], a, [0.3]), 13.5)

    def test_dynamic_and_tributary(self):
        self.assertEqual(dynamic_amplification(10, 1.2), 12)
        self.assertEqual(tributary_load(4, 8), 32)

    def test_validation(self):
        self.assertTrue(validate_load(dead_load("G", 10)))

    def test_invalid_direction(self):
        with self.assertRaises(LoadError):
            create_load("Bad", "test", 10, (0, 0, 0))

    def test_invalid_axis(self):
        with self.assertRaises(LoadError):
            load_component(dead_load("G", 10), 3)

    def test_empty_combination(self):
        with self.assertRaises(LoadError):
            combination_value([])


if __name__ == "__main__":
    unittest.main()
