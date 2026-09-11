import unittest
from phoenix.structural_solver_verification.engine import (
    beam_uniform_analytic,
    timber_design_strength,
    timber_check,
    rc_column_axial_capacity,
    solver_crosscheck_case,
)

class TestSolverVerification(unittest.TestCase):
    def test_beam_formula(self):
        r = beam_uniform_analytic(2.0, 1.0, 9000.0, 50.8, 76.2)
        self.assertAlmostEqual(r["max_moment_kNm"], 0.5, places=6)
        self.assertAlmostEqual(r["support_reaction_each_kN"], 1.0, places=6)

    def test_timber_span_sensitivity(self):
        fmd = timber_design_strength(18.0, 0.8, 1.3)
        short = timber_check(1.55, 50.8, 76.2, 0.9, 0.55, 0.4, 9000, fmd, 250)
        long = timber_check(3.40, 50.8, 76.2, 0.9, 0.55, 0.4, 9000, fmd, 250)
        self.assertEqual(short["status"], "PASS")
        self.assertEqual(long["status"], "FAIL")

    def test_column_proxy_capacity(self):
        nrd = rc_column_axial_capacity(200, 200, 4, 12, 20, 1.5, 500, 1.15)
        self.assertGreater(nrd, 600.0)
        self.assertLess(nrd, 640.0)

    def test_solver_crosscheck_acceptance(self):
        analytic = {"midspan_deflection_mm": 2.0}
        solver = {"execution": "PASS", "reaction_sum_kN": 4.0, "midspan_deflection_mm": -2.01}
        result = solver_crosscheck_case(solver, analytic, 4.0)
        self.assertEqual(result["crosscheck_status"], "PASS")

if __name__ == "__main__":
    unittest.main()
