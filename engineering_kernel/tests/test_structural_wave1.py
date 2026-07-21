from __future__ import annotations
from engineering_kernel.tests.numeric_assertions import assert_float_close, assert_numeric_sequence_close
import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.structural import *


class StructuralWave1Tests(unittest.TestCase):
    def test_rectangle_properties(self):
        assert_float_close(self, rectangle_area(2.0, 3.0), 6.0)
        assert_float_close(self, rectangle_centroid_y(3.0), 1.5)
        assert_float_close(self, rectangle_inertia_y(2.0, 3.0), 4.5)
        assert_float_close(self, rectangle_section_modulus_y(2.0, 3.0), 3.0)
        self.assertAlmostEqual(rectangle_radius_of_gyration_y(2.0, 3.0), math.sqrt(0.75))
        props = rectangle_section_properties(2.0, 3.0)
        assert_float_close(self, props.area, 6.0)

    def test_circle_properties(self):
        self.assertAlmostEqual(circle_area(2.0), math.pi)
        self.assertAlmostEqual(circle_inertia(2.0), math.pi / 4.0)
        self.assertAlmostEqual(circle_section_modulus(2.0), math.pi / 4.0)

    def test_parallel_axis(self):
        assert_float_close(self, parallel_axis_inertia(10.0, 2.0, 3.0), 28.0)

    def test_stresses(self):
        assert_float_close(self, normal_stress(100.0, 10.0), 10.0)
        assert_float_close(self, bending_stress(100.0, 2.0, 20.0), 10.0)
        assert_float_close(self, combined_normal_stress(100.0, 10.0, 100.0, 2.0, 20.0), 20.0)
        assert_float_close(self, shear_stress_average(50.0, 10.0), 5.0)

    def test_strain_and_axial_deformation(self):
        assert_float_close(self, strain_from_stress(200.0, 200000.0), 0.001)
        assert_float_close(self, axial_deformation(1000.0, 2.0, 100.0, 200.0), 0.1)

    def test_uniform_load_beam(self):
        reactions = simply_supported_reactions_uniform_load(10.0, 4.0)
        assert_numeric_sequence_close(self, reactions, (20.0, 20.0))
        assert_float_close(self, simply_supported_max_moment_uniform_load(10.0, 4.0), 20.0)
        value = simply_supported_max_deflection_uniform_load(10.0, 4.0, 200000.0, 1000.0)
        self.assertGreater(value, 0.0)

    def test_point_load_deflections(self):
        self.assertGreater(simply_supported_center_deflection_point_load(10, 4, 200000, 1000), 0)
        self.assertGreater(cantilever_end_deflection_point_load(10, 4, 200000, 1000), 0)
        self.assertGreater(cantilever_end_rotation_point_load(10, 4, 200000, 1000), 0)

    def test_column(self):
        self.assertAlmostEqual(effective_length(3.0, 0.7), 2.1, places=12)
        assert_float_close(self, slenderness_ratio(2.0, 0.1), 20.0)
        self.assertGreater(euler_buckling_load(200000.0, 1000.0, 2.0), 0.0)

    def test_second_order(self):
        assert_float_close(self, second_order_moment_amplification(100.0, 50.0, 100.0), 200.0)
        with self.assertRaises(StructuralError):
            second_order_moment_amplification(100.0, 100.0, 100.0)

    def test_utilization_and_safety(self):
        assert_float_close(self, utilization_ratio(80.0, 100.0), 0.8)
        assert_float_close(self, factor_of_safety(150.0, 100.0), 1.5)

    def test_vector_resultant(self):
        assert_float_close(self, resultant_force_2d(3.0, 4.0), 5.0)

    def test_vector_transform(self):
        gx, gy = transform_vector_2d_local_to_global(1.0, 0.0, 90.0)
        self.assertAlmostEqual(gx, 0.0, places=12)
        self.assertAlmostEqual(gy, 1.0, places=12)
        lx, ly = transform_vector_2d_global_to_local(gx, gy, 90.0)
        self.assertAlmostEqual(lx, 1.0, places=12)
        self.assertAlmostEqual(ly, 0.0, places=12)

    def test_invalid_inputs(self):
        with self.assertRaises(StructuralError):
            rectangle_area(0.0, 1.0)
        with self.assertRaises(StructuralError):
            factor_of_safety(100.0, 0.0)


if __name__ == "__main__":
    unittest.main()
