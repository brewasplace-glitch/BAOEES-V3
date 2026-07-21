from __future__ import annotations
from engineering_kernel.tests.numeric_assertions import assert_float_close, assert_numeric_sequence_close
import math
import unittest

from engineering_kernel.src.phoenix_engineering_kernel.geometry import *


class GeometryWave1Tests(unittest.TestCase):
    def test_points(self):
        self.assertEqual(point_2d(1, 2), Point2D(1, 2))
        self.assertEqual(point_3d(1, 2, 3), Point3D(1, 2, 3))

    def test_distances(self):
        self.assertAlmostEqual(distance_2d(Point2D(0,0), Point2D(3,4)), 5)
        self.assertAlmostEqual(distance_3d(Point3D(0,0,0), Point3D(1,2,2)), 3)

    def test_midpoints(self):
        self.assertEqual(midpoint_2d(Point2D(0,0), Point2D(2,4)), Point2D(1,2))
        self.assertEqual(midpoint_3d(Point3D(0,0,0), Point3D(2,4,6)), Point3D(1,2,3))

    def test_vector_products(self):
        self.assertEqual(dot_2d((1,2),(3,4)), 11)
        self.assertEqual(cross_2d((1,0),(0,1)), 1)
        assert_numeric_sequence_close(self, cross_3d((1,0,0),(0,1,0)), (0,0,1))

    def test_normalize(self):
        assert_numeric_sequence_close(self, normalize_vector_2d((3,4)), (0.6,0.8))
        result=normalize_vector_3d((0,0,2))
        assert_numeric_sequence_close(self, result, (0.0,0.0,1.0))

    def test_zero_vector_rejected(self):
        with self.assertRaises(GeometryError):
            normalize_vector_2d((0,0))

    def test_angle(self):
        self.assertAlmostEqual(angle_between_vectors_2d((1,0),(0,1)), math.pi/2)

    def test_polygon(self):
        square=[Point2D(0,0),Point2D(2,0),Point2D(2,2),Point2D(0,2)]
        self.assertAlmostEqual(polygon_area(square),4)
        self.assertAlmostEqual(polygon_perimeter(square),8)
        self.assertEqual(polygon_centroid(square),Point2D(1,1))

    def test_bounding_box(self):
        box=bounding_box_2d([Point2D(-1,3),Point2D(4,-2)])
        self.assertEqual(box.minimum,Point2D(-1,-2))
        self.assertEqual(box.maximum,Point2D(4,3))
        self.assertEqual(box.width,5)
        self.assertEqual(box.height,5)

    def test_translate_rotate(self):
        self.assertEqual(translate_2d(Point2D(1,2),3,-1),Point2D(4,1))
        p=rotate_2d(Point2D(1,0),math.pi/2)
        self.assertAlmostEqual(p.x,0,places=12)
        self.assertAlmostEqual(p.y,1,places=12)

    def test_line_intersection(self):
        p=line_intersection_2d(Point2D(0,0),Point2D(2,2),Point2D(0,2),Point2D(2,0))
        self.assertAlmostEqual(p.x,1)
        self.assertAlmostEqual(p.y,1)

    def test_parallel_lines_rejected(self):
        with self.assertRaises(GeometryError):
            line_intersection_2d(Point2D(0,0),Point2D(1,0),Point2D(0,1),Point2D(1,1))

    def test_non_finite_rejected(self):
        with self.assertRaises(GeometryError):
            Point2D(float("nan"),0)


if __name__ == "__main__":
    unittest.main()
