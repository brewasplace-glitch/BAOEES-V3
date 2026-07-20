import math
import unittest
from engineering_kernel.src.phoenix_engineering_kernel.units import *

class UnitsTests(unittest.TestCase):
    def test_length(self): self.assertAlmostEqual(convert_length(1500,"mm","m"),1.5)
    def test_area(self): self.assertAlmostEqual(convert_area(1000000,"mm2","m2"),1.0)
    def test_force(self): self.assertAlmostEqual(convert_force(2.5,"kN","N"),2500)
    def test_pressure_alias(self): self.assertAlmostEqual(convert_pressure(30,"N/mm2","MPa"),30)
    def test_temperature(self): self.assertAlmostEqual(convert_temperature(20,"degC","K"),293.15)
    def test_angle(self): self.assertAlmostEqual(convert_angle(180,"deg","rad"),math.pi)
    def test_quantity(self): self.assertAlmostEqual(quantity(500,"mm").convert_to("m").value,0.5)
    def test_compatibility(self): self.assertTrue(are_compatible("kPa","MPa"))
    def test_incompatible(self):
        with self.assertRaises(UnitError): convert(1,"m","kN")
    def test_nonfinite(self):
        with self.assertRaises(UnitError): quantity(float("nan"),"m")
