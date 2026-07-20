from __future__ import annotations

import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.concrete import *


class ConcreteWave1Tests(unittest.TestCase):
    def test_concrete_properties(self):
        self.assertAlmostEqual(concrete_design_strength(30.0, 0.85, 1.5), 17.0)
        self.assertAlmostEqual(concrete_mean_tensile_strength(30.0), 2.8964681538, places=9)
        self.assertAlmostEqual(concrete_elastic_modulus(38.0), 32836.5680313, places=7)
        self.assertAlmostEqual(concrete_unit_weight(), 23.53596)
        self.assertAlmostEqual(concrete_section_self_weight(0.3, 0.5), 3.6)

    def test_steel_and_reinforcement(self):
        self.assertAlmostEqual(steel_design_strength(500.0, 1.15), 434.7826086957, places=9)
        self.assertAlmostEqual(bar_area(16.0), math.pi * 64.0)
        self.assertAlmostEqual(total_reinforcement_area(16.0, 4), math.pi * 256.0)
        self.assertAlmostEqual(reinforcement_ratio(1000.0, 300.0, 500.0), 1.0 / 150.0)

    def test_flexure(self):
        d = effective_depth(600.0, 35.0, 10.0, 20.0)
        self.assertAlmostEqual(d, 545.0)
        z = lever_arm(d)
        self.assertAlmostEqual(z, 490.5)
        required = required_tension_reinforcement(200.0, 435.0, z)
        self.assertAlmostEqual(required, 937.3498775587, places=7)
        self.assertAlmostEqual(minimum_reinforcement_area(0.0013, 300.0, 500.0), 195.0, places=12)
        self.assertAlmostEqual(maximum_reinforcement_area(0.04, 300.0, 500.0), 6000.0, places=12)
        self.assertAlmostEqual(flexural_utilization(1000.0, 800.0), 0.8, places=12)

    def test_shear(self):
        self.assertAlmostEqual(concrete_shear_stress(150.0, 300.0, 500.0), 1.0)
        self.assertAlmostEqual(concrete_shear_capacity(0.6, 300.0, 500.0), 90.0)
        demand = required_shear_reinforcement_per_length(120.0, 435.0, 450.0)
        self.assertAlmostEqual(demand, 0.61302682, places=8)
        self.assertAlmostEqual(stirrup_spacing(157.0, demand), 256.10625, places=5)
        self.assertAlmostEqual(shear_utilization(90.0, 120.0), 0.75, places=12)

    def test_columns(self):
        concrete = axial_concrete_capacity(17.0, 250000.0, 0.8)
        steel = axial_steel_capacity(435.0, 4000.0)
        self.assertAlmostEqual(concrete, 3400.0, places=12)
        self.assertAlmostEqual(steel, 1740.0, places=12)
        self.assertAlmostEqual(combined_axial_capacity(concrete, steel), 5140.0, places=12)
        self.assertAlmostEqual(column_slenderness(3000.0, 100.0), 30.0, places=12)
        self.assertAlmostEqual(interaction_index(1000.0, 2000.0, 100.0, 200.0), 1.0, places=12)

    def test_serviceability(self):
        self.assertAlmostEqual(crack_control_ratio(1200.0, 1000.0), 1.2, places=12)
        self.assertAlmostEqual(deflection_utilization(12.0, 15.0), 0.8, places=12)
        self.assertAlmostEqual(nominal_cover(30.0, 10.0), 40.0, places=12)
        lb = anchorage_length(16.0, 435.0, 2.5)
        self.assertAlmostEqual(lb, 696.0, places=12)
        self.assertAlmostEqual(development_length(lb, [0.8, 1.1]), 612.48)
        self.assertTrue(serviceability_passes(0.8))
        self.assertFalse(serviceability_passes(1.2))

    def test_invalid(self):
        with self.assertRaises(ConcreteDesignError):
            effective_depth(100.0, 60.0, 20.0, 50.0)
        with self.assertRaises(ConcreteDesignError):
            total_reinforcement_area(16.0, 0)
        with self.assertRaises(ConcreteDesignError):
            development_length(500.0, [])


if __name__ == "__main__":
    unittest.main()
