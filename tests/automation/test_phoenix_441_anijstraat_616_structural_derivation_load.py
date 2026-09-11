import unittest
from phoenix.structural_derivation_load.engine import cumulative,qref,wall_line_weight
class T(unittest.TestCase):
    def test_grid(self):
        self.assertAlmostEqual(cumulative([4.15,.65,.45,1.55,1,1,1.15,.35,1.9,3.4,.5,2])[-1],18.10)
        self.assertAlmostEqual(cumulative([2.9,1,1,.55,2.15,3.6,2.5])[-1],13.70)
    def test_wind(self):
        self.assertAlmostEqual(qref(30),.5513,4); self.assertAlmostEqual(qref(40),.98,4)
    def test_walls(self):
        self.assertAlmostEqual(wall_line_weight(.1,3.48,20),6.96)
        self.assertAlmostEqual(wall_line_weight(.15,3.48,20),10.44)
if __name__=="__main__": unittest.main()
