from __future__ import annotations
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.materials import *


class MaterialsWave1Tests(unittest.TestCase):
    def test_create_material(self):
        m = create_material("Generic", "test", 1000, 5000, 0.25)
        self.assertEqual(m.name, "Generic")

    def test_concrete(self):
        m = concrete_material("C-test", 2400, 30000, 30, 2.9)
        self.assertEqual(classify_material(m), "concrete")

    def test_steel(self):
        m = structural_steel_material("S-test", 355, 510)
        self.assertEqual(m.density, 7850)

    def test_other_material_factories(self):
        self.assertEqual(classify_material(reinforcement_steel_material("B", 500, 550)), "reinforcement_steel")
        self.assertEqual(classify_material(timber_material("T", 450, 11000, 20, 24, 4)), "timber")
        self.assertEqual(classify_material(masonry_material("M", 1800, 5000, 10, 0.5)), "masonry")
        self.assertEqual(classify_material(aluminium_material("A", 250)), "aluminium")
        self.assertEqual(classify_material(glass_material("G", 45)), "glass")
        self.assertEqual(classify_material(plastic_material("P", 1200, 3000, 50, 0.35)), "plastic")
        self.assertEqual(classify_material(soil_material("S", 1900, 25000, 35, 0.30)), "soil")

    def test_moduli(self):
        self.assertAlmostEqual(shear_modulus(210000, 0.3), 80769.230769, places=5)
        self.assertAlmostEqual(bulk_modulus(210000, 0.3), 175000)

    def test_specific_weight(self):
        self.assertAlmostEqual(specific_weight(1000), 9806.65)

    def test_stress_strain(self):
        self.assertEqual(stress(1000, 100), 10)
        self.assertEqual(strain(2, 1000), 0.002)
        self.assertEqual(elastic_stress(200000, 0.001), 200)
        self.assertEqual(elastic_strain(200, 200000), 0.001)

    def test_design_values(self):
        self.assertEqual(characteristic_to_design_value(30, 1.5), 20)
        self.assertEqual(design_to_characteristic_value(20, 1.5), 30)

    def test_safety_and_utilization(self):
        self.assertEqual(safety_factor(150, 100), 1.5)
        self.assertEqual(utilization_ratio(80, 100), 0.8)

    def test_environmental_factors(self):
        self.assertEqual(apply_temperature_factor(100, 0.8), 80)
        self.assertEqual(apply_moisture_factor(100, 0.9), 90)

    def test_thermal(self):
        self.assertAlmostEqual(thermal_strain(12e-6, 50), 0.0006)
        self.assertAlmostEqual(thermal_expansion_length(10, 12e-6, 50), 0.006)

    def test_creep_and_shrinkage(self):
        self.assertEqual(creep_adjusted_modulus(30000, 2), 10000)
        self.assertAlmostEqual(shrinkage_deformation(10, -0.0003), -0.003, places=12)

    def test_adjusted_material(self):
        m = create_material("Generic", "test", 1000, 5000, 0.25)
        adjusted = adjusted_material(m, moisture_factor=0.9, temperature_factor=0.8)
        self.assertEqual(adjusted.moisture_factor, 0.9)
        self.assertEqual(adjusted.temperature_factor, 0.8)

    def test_validation(self):
        m = create_material("Generic", "test", 1000, 5000, 0.25)
        self.assertTrue(validate_material(m))

    def test_invalid_poisson_ratio(self):
        with self.assertRaises(MaterialError):
            create_material("Bad", "test", 1000, 5000, 0.5)

    def test_zero_area_rejected(self):
        with self.assertRaises(MaterialError):
            stress(10, 0)


if __name__ == "__main__":
    unittest.main()
