import unittest
from phoenix.structural_3d_report.engine import project_iso,validate_inputs
class T(unittest.TestCase):
 def test_iso(self):
  self.assertEqual(project_iso(0,0,0),(430.0,80.0));self.assertGreater(project_iso(1,0,0)[0],430)
 def test_source_guard(self):
  d={'status':'PASS_PRELIMINARY_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS','source_sha256':'A'};s={'status':'PASS_REAL_OPEN_SOURCE_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION','source_sha256':'A'};r={'status':'PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AND_LOAD_MODEL','source':{'sha256':'A'}}
  with self.assertRaises(RuntimeError): validate_inputs(d,s,r,'B')
if __name__=='__main__':unittest.main()
