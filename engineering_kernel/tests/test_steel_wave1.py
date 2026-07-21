from __future__ import annotations

import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.steel import *
from engineering_kernel.tests.numeric_assertions import assert_float_close


class SteelWave1Tests(unittest.TestCase):
    def test_material_and_basic_mechanics(self):
        assert_float_close(self, steel_design_strength(355.0, 1.1), 322.72727272727275)
        assert_float_close(self, shear_modulus(210000.0, 0.3), 80769.23076923077)
        assert_float_close(self, thermal_strain(12e-6, 40.0), 0.00048)
        assert_float_close(self, steel_member_self_weight(2000.0), 0.153964405)
        assert_float_close(self, normal_stress(200.0, 1000.0), 200.0)
        assert_float_close(self, shear_stress(90.0, 600.0), 150.0)
        assert_float_close(self, elastic_strain(210.0, 210000.0), 0.001)
        assert_float_close(self, von_mises_stress(100.0, 40.0, 30.0), math.sqrt(10300.0))

    def test_section_properties(self):
        assert_float_close(self, rectangular_second_moment(200.0, 300.0), 450000000.0)
        assert_float_close(self, rectangular_elastic_section_modulus(200.0, 300.0), 3000000.0)
        assert_float_close(self, rectangular_plastic_section_modulus(200.0, 300.0), 4500000.0)
        assert_float_close(self, circular_second_moment(100.0), math.pi * 100.0**4 / 64.0)
        assert_float_close(self, circular_elastic_section_modulus(100.0), math.pi * 100.0**3 / 32.0)
        assert_float_close(self, radius_of_gyration(8_000_000.0, 2000.0), math.sqrt(4000.0))

    def test_stability(self):
        assert_float_close(self, member_slenderness(3000.0, 60.0), 50.0)
        euler = euler_buckling_load(210000.0, 8_000_000.0, 3000.0)
        assert_float_close(self, euler, math.pi**2 * 210000.0 * 8_000_000.0 / 3000.0**2 / 1000.0)
        nondim = non_dimensional_slenderness(2000.0, 355.0, euler)
        assert_float_close(self, nondim, math.sqrt(710.0 / euler))
        chi = buckling_reduction_factor(1.0, 0.34)
        self.assertGreater(chi, 0.0)
        self.assertLessEqual(chi, 1.0)
        assert_float_close(self, lateral_torsional_reduction(1.0, 0.34), chi)

    def test_member_resistances(self):
        gross = gross_tension_resistance(2000.0, 355.0, 1.0)
        net = net_tension_resistance(1700.0, 510.0, 1.25, 0.9)
        assert_float_close(self, gross, 710.0)
        assert_float_close(self, net, 624.24)
        assert_float_close(self, tension_resistance(gross, net), 624.24)
        assert_float_close(self, compression_resistance(2000.0, 355.0, 0.8, 1.0), 568.0)
        assert_float_close(self, bending_resistance(3_000_000.0, 355.0, 1.0), 1065.0)
        assert_float_close(self, shear_resistance(1200.0, 355.0, 1.0), 1200.0 * 355.0 / math.sqrt(3.0) / 1000.0)
        assert_float_close(self, lateral_torsional_bending_resistance(1065.0, 0.75), 798.75)
        assert_float_close(self, axial_bending_interaction(200.0, 800.0, 100.0, 400.0), 0.5)
        assert_float_close(self, plate_slenderness(300.0, 12.0), 25.0)

    def test_bolts(self):
        shear = bolt_shear_resistance(245.0, 800.0, 0.6, 1.25, 2)
        tension = bolt_tension_resistance(245.0, 800.0, 0.9, 1.25)
        bearing = bolt_bearing_resistance(20.0, 10.0, 430.0, 2.0, 1.25)
        assert_float_close(self, shear, 188.16)
        assert_float_close(self, tension, 141.12)
        assert_float_close(self, bearing, 137.6)
        assert_float_close(self, combined_bolt_utilization(94.08, shear, 70.56, tension), 0.5)
        self.assertEqual(required_bolt_count(500.0, 188.16), 3)

    def test_welds_connections_and_serviceability(self):
        throat = weld_effective_throat(8.0)
        assert_float_close(self, throat, 8.0 / math.sqrt(2.0))
        assert_float_close(self, weld_resistance(throat, 200.0, 180.0), throat * 200.0 * 180.0 / 1000.0)
        assert_float_close(self, connection_utilization([50.0, 20.0], [100.0, 80.0]), 0.75)
        assert_float_close(self, deflection_utilization(12.0, 15.0), 0.8)
        assert_float_close(self, fatigue_range_utilization(60.0, 80.0), 0.75)
        self.assertTrue(utilization_passes(1.0))
        self.assertFalse(utilization_passes(1.01))

    def test_invalid_inputs(self):
        with self.assertRaises(SteelDesignError):
            shear_modulus(210000.0, 0.5)
        with self.assertRaises(SteelDesignError):
            required_bolt_count(100.0, 0.0)
        with self.assertRaises(SteelDesignError):
            connection_utilization([1.0], [1.0, 2.0])
        with self.assertRaises(SteelDesignError):
            bolt_shear_resistance(245.0, 800.0, 0.6, 1.25, 0)


if __name__ == "__main__":
    unittest.main()
