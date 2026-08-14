from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from phoenix.autonomy.structural_golden_reference_suite_v1_0 import *

def defs():
    b={"id":"B","idealization":"SIMPLY_SUPPORTED_BEAM_UDL","inputs":{"q_N_per_m":1000.0,"L_m":5.0},"expected":{"total_load_N":5000.0,"reaction_each_N":2500.0,"max_moment_Nm":3125.0},"calculix":{"element_count":100,"validation_status":"CALCULIX_GOLDEN_REFERENCE_VALIDATED","software_test_tolerance_N":5.0}}
    E=210e9; I=0.1*0.1**3/12
    c={"id":"C","idealization":"CANTILEVER_END_POINT_LOAD","inputs":{"P_N":1000.0,"L_m":2.0,"E_Pa":E,"I_m4":I,"section_b_m":0.1,"section_h_m":0.1},"expected":{"reaction_N":1000.0,"fixed_end_moment_Nm":2000.0,"tip_deflection_m":1000*8/(3*E*I)},"calculix":{"element_count":40,"validation_status":"PENDING","numerical_tolerance":"REQUIRED"}}
    a={"id":"A","idealization":"AXIAL_BAR","inputs":{"P_N":100000.0,"L_m":2.0,"E_Pa":200e9,"A_m2":0.01},"expected":{"axial_stress_Pa":1e7,"elongation_m":0.0001},"calculix":{"element_count":20,"validation_status":"PENDING","numerical_tolerance":"REQUIRED"}}
    return b,c,a

class T(unittest.TestCase):
    def test_01_beam(self): self.assertEqual(ANALYTICAL_VALIDATED,analytical(defs()[0])["status"])
    def test_02_beam_values(self): self.assertEqual(3125.0,analytical(defs()[0])["computed"]["max_moment_Nm"])
    def test_03_cant(self): self.assertEqual(ANALYTICAL_VALIDATED,analytical(defs()[1])["status"])
    def test_04_axial(self): self.assertEqual(ANALYTICAL_VALIDATED,analytical(defs()[2])["status"])
    def test_05_axial_values(self): self.assertEqual(0.0001,analytical(defs()[2])["computed"]["elongation_m"])
    def test_06_bad_expected(self):
        d=defs()[0]; d["expected"]["reaction_each_N"]=1; self.assertEqual(ANALYTICAL_FAILED,analytical(d)["status"])
    def test_07_beam_deck(self):
        with tempfile.TemporaryDirectory() as td:self.assertIn("*ELEMENT, TYPE=B31",Path(deck(defs()[0],Path(td))["deck"]).read_text())
    def test_08_cant_deck(self):
        with tempfile.TemporaryDirectory() as td:self.assertIn("*NODE PRINT, NSET=TIP",Path(deck(defs()[1],Path(td))["deck"]).read_text())
    def test_09_axial_deck(self):
        with tempfile.TemporaryDirectory() as td:self.assertIn("*ELEMENT, TYPE=T3D2",Path(deck(defs()[2],Path(td))["deck"]).read_text())
    def test_10_no_live(self):
        with tempfile.TemporaryDirectory() as td:self.assertFalse(deck(defs()[0],Path(td))["live_solver_started"])
    def test_11_tolerance_required(self): self.assertEqual("REQUIRED",defs()[1]["calculix"]["numerical_tolerance"])
    def test_12_safety(self):
        self.assertFalse(SAFETY["automatic_professional_approval"]); self.assertFalse(SAFETY["automatic_code_compliance_claim"]); self.assertEqual("LOCKED",SAFETY["production_release"]); self.assertEqual("LOCKED",SAFETY["for_construction_release"])
if __name__=="__main__":unittest.main()
