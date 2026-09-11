import unittest
from phoenix.structural_design_consolidation.engine import timber_utilization, rc_flexure_proxy

class TestStructuralDesignConsolidation(unittest.TestCase):
    def test_50x150_at_3p4m_passes_proxy(self):
        r=timber_utilization(3.4,50,150,0.9,0.55,0.4,9000,18,0.8,1.3,250)
        self.assertEqual(r["status"],"PASS")
        self.assertLess(r["governing_utilization"],1.0)

    def test_50x125_at_3p4m_fails_proxy(self):
        r=timber_utilization(3.4,50,125,0.9,0.55,0.4,9000,18,0.8,1.3,250)
        self.assertEqual(r["status"],"FAIL")

    def test_ringbeam_proxy_capacity(self):
        r=rc_flexure_proxy(150,200,2,12,25,500,1.15)
        self.assertGreater(r["M_Rd_proxy_kNm"],12.0)
        self.assertLess(r["M_Rd_proxy_kNm"],14.0)

if __name__=="__main__":
    unittest.main()
