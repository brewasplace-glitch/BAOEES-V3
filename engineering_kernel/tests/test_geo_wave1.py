from __future__ import annotations
from engineering_kernel.tests.numeric_assertions import assert_float_close
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.geo import *


class GeoWave1Tests(unittest.TestCase):
    def setUp(self):
        self.layer = create_soil_layer("Sand", 0.0, -2.0, 18.0, 20.0, 30.0, 0.0, 10000.0)

    def test_layer(self):
        assert_float_close(self, layer_thickness(self.layer), 2.0)
        self.assertTrue(validate_soil_profile([self.layer]))

    def test_stresses(self):
        self.assertAlmostEqual(submerged_unit_weight(20.0), 10.19)
        self.assertAlmostEqual(pore_water_pressure(2.0), 19.62)
        assert_float_close(self, total_vertical_stress(18.0, 2.0), 36.0)
        assert_float_close(self, effective_vertical_stress(36.0, 10.0), 26.0)
        assert_float_close(self, stress_increment_uniform_load(100.0, 0.5), 50.0)

    def test_effective_profile(self):
        value = effective_stress_profile([self.layer], 2.0, 1.0)
        self.assertAlmostEqual(value, 28.19)

    def test_rankine(self):
        self.assertAlmostEqual(rankine_active_coefficient(30.0), 1/3, places=12)
        self.assertAlmostEqual(rankine_passive_coefficient(30.0), 3.0, places=12)
        self.assertAlmostEqual(rankine_at_rest_coefficient(30.0), 0.5, places=12)

    def test_lateral_pressure(self):
        self.assertAlmostEqual(lateral_earth_pressure(30.0, 1/3), 10.0)
        assert_float_close(self, triangular_pressure_resultant(10.0, 3.0), 15.0)
        assert_float_close(self, triangular_pressure_application_height(3.0), 1.0)

    def test_bearing_factors(self):
        assert_float_close(self, bearing_capacity_factor_nq(0.0), 1.0)
        assert_float_close(self, bearing_capacity_factor_nc(0.0), 5.14)
        assert_float_close(self, bearing_capacity_factor_ngamma(0.0), 0.0)

    def test_bearing_capacity(self):
        qult = ultimate_bearing_capacity_strip(0.0, 20.0, 18.0, 1.0, 0.0)
        assert_float_close(self, qult, 20.0)
        assert_float_close(self, allowable_bearing_capacity(300.0, 3.0), 100.0)

    def test_settlement(self):
        assert_float_close(self, one_dimensional_settlement(100.0, 2.0, 10000.0), 0.02)
        value = elastic_settlement(100.0, 1.0, 10000.0, 0.3)
        self.assertAlmostEqual(value, 0.0091)

    def test_consolidation(self):
        assert_float_close(self, consolidation_degree_time_factor(0.0), 0.0)
        self.assertGreater(consolidation_degree_time_factor(0.1), 0.0)

    def test_seepage(self):
        assert_float_close(self, hydraulic_gradient(2.0, 4.0), 0.5)
        assert_float_close(self, darcy_velocity(1e-5, 0.5), 5e-6)
        assert_float_close(self, seepage_discharge(1e-5, 0.5, 10.0), 5e-5)
        self.assertAlmostEqual(critical_hydraulic_gradient(20.0), 10.19/9.81)

    def test_liquefaction(self):
        assert_float_close(self, liquefaction_safety_factor(0.2, 0.1), 2.0)

    def test_slope(self):
        assert_float_close(self, slope_ratio(2.0, 1.0), 2.0)
        self.assertAlmostEqual(slope_angle_deg(1.0, 1.0), 45.0)

    def test_groundwater(self):
        assert_float_close(self, groundwater_elevation(0.0, 0.5), -0.5)

    def test_invalid_layer(self):
        with self.assertRaises(GeoError):
            create_soil_layer("Bad", 0.0, 1.0, 18.0, 20.0)

    def test_profile_gap(self):
        second = create_soil_layer("Clay", -2.1, -3.0, 17.0, 19.0)
        self.assertFalse(validate_soil_profile([self.layer, second]))


if __name__ == "__main__":
    unittest.main()
