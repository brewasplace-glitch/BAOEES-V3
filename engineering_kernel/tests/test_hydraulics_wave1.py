from __future__ import annotations
import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.hydraulics import *


class HydraulicsWave1Tests(unittest.TestCase):
    def test_rainfall(self):
        self.assertEqual(rainfall_depth(20.0, 2.0), 40.0)
        self.assertEqual(rainfall_volume(100.0, 10.0), 1.0)
        self.assertEqual(runoff_volume(100.0, 10.0, 0.8), 0.8)

    def test_rational_method(self):
        self.assertAlmostEqual(rational_method_flow(1.0, 36.0, 100.0), 0.001)

    def test_weighted_runoff(self):
        self.assertAlmostEqual(weighted_runoff_coefficient([100, 100], [0.5, 1.0]), 0.75)

    def test_circular_geometry(self):
        self.assertAlmostEqual(circular_area(2.0), math.pi)
        self.assertAlmostEqual(circular_wetted_perimeter_full(2.0), 2 * math.pi)
        self.assertEqual(circular_hydraulic_radius_full(2.0), 0.5)

    def test_rectangular_geometry(self):
        self.assertEqual(rectangular_area(2.0, 1.0), 2.0)
        self.assertEqual(rectangular_wetted_perimeter(2.0, 1.0), 4.0)
        self.assertEqual(hydraulic_radius(2.0, 4.0), 0.5)

    def test_manning(self):
        v = manning_velocity(0.5, 0.01, 0.02)
        self.assertGreater(v, 0.0)
        self.assertAlmostEqual(manning_discharge(2.0, 0.5, 0.01, 0.02), 2.0 * v)
        self.assertGreater(full_pipe_manning_discharge(1.0, 0.01, 0.013), 0.0)

    def test_chezy(self):
        self.assertEqual(chezy_velocity(50.0, 1.0, 0.01), 5.0)

    def test_flow_velocity(self):
        self.assertEqual(discharge_from_velocity(2.0, 3.0), 6.0)
        self.assertEqual(velocity_from_discharge(6.0, 2.0), 3.0)
        self.assertEqual(travel_time(12.0, 3.0), 4.0)

    def test_storage(self):
        self.assertEqual(storage_volume(2.0, 1.0, 10.0), 10.0)
        self.assertEqual(detention_time(10.0, 2.0), 5.0)

    def test_infiltration(self):
        self.assertEqual(infiltration_volume(10.0, 100.0, 1.0), 1.0)
        self.assertEqual(required_infiltration_area(1.0, 10.0, 1.0), 100.0)

    def test_darcy_and_pump(self):
        self.assertEqual(darcy_flow(1e-5, 0.5, 10.0), 5e-5)
        self.assertEqual(pump_capacity(10.0, 5.0), 2.0)

    def test_outlets(self):
        self.assertEqual(number_of_outlets(0.021, 0.01), 3)
        self.assertEqual(roof_outlet_flow(100.0, 36.0), 0.001)

    def test_balance(self):
        self.assertEqual(water_balance(10.0, 6.0, 2.0, 1.0), 1.0)
        self.assertEqual(continuity_error(10.0, 6.0, 4.0), 0.0)

    def test_pipe_design(self):
        self.assertEqual(pipe_fill_ratio(0.5, 1.0), 0.5)
        self.assertEqual(required_pipe_area(2.0, 4.0), 0.5)
        self.assertAlmostEqual(equivalent_circular_diameter(math.pi), 2.0)

    def test_drainage_coefficient(self):
        self.assertAlmostEqual(drainage_specific_discharge(8.64), 1e-7)

    def test_invalid(self):
        with self.assertRaises(HydraulicsError):
            rational_method_flow(1.1, 10.0, 100.0)
        with self.assertRaises(HydraulicsError):
            weighted_runoff_coefficient([1.0], [0.5, 0.6])


if __name__ == "__main__":
    unittest.main()
