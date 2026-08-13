from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from phoenix.integrations.calculix.reaction_equilibrium_hardening_v1_1 import *

DAT="""forces (fx,fy,fz) for set SUPPORTS and time 1
1 0 0 2.475000E+03
101 0 0 2.475000E+03
total force (fx,fy,fz) for set SUPPORTS and time 1
0 0 4.950000E+03
"""

def inp_text():
    lines=["*NSET, NSET=SUPPORTS","1, 101","*CLOAD"]
    for i in range(101):
        lines.append(f"{i+1}, 3, {-25.0 if i in (0,100) else -50.0}")
    return "\n".join(lines)+"\n"

class T(unittest.TestCase):
    def pair(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        d=root/"x.dat"; d.write_text(DAT,encoding="utf-8")
        i=root/"x.inp"; i.write_text(inp_text(),encoding="utf-8")
        return td,d,i

    def test_01_dat_total(self):
        td,d,i=self.pair()
        try:self.assertEqual(4950.0,parse_support_forces_dat(d)["reported_total_force_z_N"])
        finally:td.cleanup()

    def test_02_support_rows(self):
        td,d,i=self.pair()
        try:
            r=parse_support_forces_dat(d)
            self.assertEqual(2475.0,r["support_rows"][1][2])
            self.assertEqual(2475.0,r["support_rows"][101][2])
        finally:td.cleanup()

    def test_03_total_cload(self):
        td,d,i=self.pair()
        try:self.assertEqual(-5000.0,parse_support_nodes_and_cloads(i)["vertical_cload_total_N"])
        finally:td.cleanup()

    def test_04_direct_support_cload(self):
        td,d,i=self.pair()
        try:self.assertEqual(-50.0,parse_support_nodes_and_cloads(i)["vertical_support_cload_total_N"])
        finally:td.cleanup()

    def test_05_total_reconstruction(self):
        td,d,i=self.pair()
        try:
            r=reconstruct_equilibrium(parse_support_forces_dat(d),parse_support_nodes_and_cloads(i))
            self.assertEqual(VALIDATED,r["status"])
            self.assertEqual(5000.0,r["reconstructed_total_support_reaction_z_N"])
        finally:td.cleanup()

    def test_06_each_support(self):
        td,d,i=self.pair()
        try:
            r=reconstruct_equilibrium(parse_support_forces_dat(d),parse_support_nodes_and_cloads(i))
            self.assertEqual(2500.0,r["reconstructed_support_reaction_by_node_N"]["1"])
            self.assertEqual(2500.0,r["reconstructed_support_reaction_by_node_N"]["101"])
        finally:td.cleanup()

    def test_07_balance_zero(self):
        td,d,i=self.pair()
        try:
            r=reconstruct_equilibrium(parse_support_forces_dat(d),parse_support_nodes_and_cloads(i))
            self.assertEqual(0.0,r["global_vertical_balance_error_N"])
        finally:td.cleanup()

    def test_08_missing_dat(self):
        self.assertEqual(DAT_PARSE_REQUIRED,parse_support_forces_dat(Path("missing.dat"))["status"])

    def test_09_reevaluate_no_solver(self):
        td,d,i=self.pair()
        try:
            r=reevaluate_existing(d,i,Path(td.name)/"out.json")
            self.assertFalse(r["reevaluation"]["live_solver_started"])
            self.assertFalse(r["reevaluation"]["raw_solver_evidence_modified"])
        finally:td.cleanup()

    def test_10_raw_immutable(self):
        self.assertFalse(SAFETY["raw_solver_evidence_overwritten"])

    def test_11_tolerance_not_general(self):
        self.assertFalse(SAFETY["software_test_tolerance_is_general_engineering_tolerance"])

    def test_12_locks(self):
        self.assertEqual("LOCKED",SAFETY["production_release"])
        self.assertEqual("LOCKED",SAFETY["for_construction_release"])
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])

if __name__=="__main__":
    unittest.main()
