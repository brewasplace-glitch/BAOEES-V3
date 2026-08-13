from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.autonomy.structural_analytical_verification_v1_0 import (
    PASS, INPUT_REQUIRED, SCOPE_NOT_SUPPORTED,
    simply_supported_beam_udl, cantilever_end_point_load, axial_bar,
    evaluate, golden_beam_check, SAFETY as AN_SAFETY,
)
from phoenix.integrations.calculix.reference_verification_v1_0 import (
    PREPARED, AUTH_REQUIRED, TEST_MODE_BLOCKED, SOLVER_NOT_FOUND,
    VALIDATED, PARSE_REQUIRED,
    build_golden_beam_deck, discover_ccx, parse_reaction_total,
    run_golden_beam, SAFETY as CCX_SAFETY,
)

class AnalyticalAndCalculixExpansionTests(unittest.TestCase):
    def test_01_ss_beam_udl(self):
        r = simply_supported_beam_udl(1000.0, 5.0)
        self.assertAlmostEqual(5000.0, r["total_load_N"])
        self.assertAlmostEqual(2500.0, r["reaction_each_N"])
        self.assertAlmostEqual(3125.0, r["max_moment_Nm"])

    def test_02_cantilever_point_load(self):
        r = cantilever_end_point_load(1000.0, 2.0)
        self.assertEqual(1000.0, r["reaction_N"])
        self.assertEqual(2000.0, r["fixed_end_moment_Nm"])
        self.assertIsNone(r["tip_deflection_m"])

    def test_03_cantilever_deflection_when_EI_present(self):
        r = cantilever_end_point_load(1000.0, 2.0, 200e9, 1e-5)
        self.assertAlmostEqual(1000*8/(3*200e9*1e-5), r["tip_deflection_m"])

    def test_04_cantilever_partial_EI_rejected(self):
        r = evaluate("CANTILEVER_END_POINT_LOAD", {"P_N": 1, "L_m": 1, "E_Pa": 200e9})
        self.assertEqual(INPUT_REQUIRED, r["status"])

    def test_05_axial_bar(self):
        r = axial_bar(100000.0, 2.0, 200e9, 0.01)
        self.assertAlmostEqual(1e7, r["axial_stress_Pa"])
        self.assertAlmostEqual(0.0001, r["elongation_m"])

    def test_06_negative_input_rejected(self):
        r = evaluate("SIMPLY_SUPPORTED_BEAM_UDL", {"q_N_per_m": -1, "L_m": 5})
        self.assertEqual(INPUT_REQUIRED, r["status"])

    def test_07_unsupported_scope_not_forced(self):
        r = evaluate("PLATE", {})
        self.assertEqual(SCOPE_NOT_SUPPORTED, r["status"])

    def test_08_golden_beam_analytical_exact(self):
        self.assertEqual(PASS, golden_beam_check()["status"])

    def test_09_deck_generation_exact_total_load(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_golden_beam_deck(Path(td), 100)
            self.assertEqual(PREPARED, r["status"])
            self.assertAlmostEqual(-5000.0, r["applied_total_load_N"])
            self.assertTrue(Path(r["deck"]).is_file())

    def test_10_deck_has_100_elements(self):
        with tempfile.TemporaryDirectory() as td:
            r = build_golden_beam_deck(Path(td), 100)
            text = Path(r["deck"]).read_text(encoding="ascii")
            section = text.split("*ELEMENT, TYPE=B31, ELSET=EALL\n",1)[1].split("*MATERIAL",1)[0]
            rows = [x for x in section.splitlines() if x.strip()]
            self.assertEqual(100, len(rows))

    def test_11_deck_mesh_minimum_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                build_golden_beam_deck(Path(td), 1)

    def test_12_no_live_without_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            old = os.environ.pop("PHOENIX_TEST_MODE", None)
            try:
                r = run_golden_beam(Path(td), allow_live_solver=False)
            finally:
                if old is not None: os.environ["PHOENIX_TEST_MODE"] = old
            self.assertEqual(AUTH_REQUIRED, r["status"])
            self.assertFalse(r["live_execution_started"])

    def test_13_test_mode_blocks_live(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"PHOENIX_TEST_MODE":"1"}):
                r = run_golden_beam(Path(td), allow_live_solver=True)
            self.assertEqual(TEST_MODE_BLOCKED, r["status"])
            self.assertFalse(r["live_execution_started"])

    @patch("phoenix.integrations.calculix.reference_verification_v1_0.discover_ccx")
    def test_14_missing_ccx_is_explicit(self, disc):
        disc.return_value = None
        with tempfile.TemporaryDirectory() as td:
            old = os.environ.pop("PHOENIX_TEST_MODE", None)
            try:
                r = run_golden_beam(Path(td), allow_live_solver=True)
            finally:
                if old is not None: os.environ["PHOENIX_TEST_MODE"] = old
            self.assertEqual(SOLVER_NOT_FOUND, r["status"])

    def test_15_parse_totals_line(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.dat"
            p.write_text("forces\n TOTALS   0.0 0.0 5.000000E+03\n", encoding="utf-8")
            r=parse_reaction_total(p)
            self.assertEqual("PARSED", r["status"])
            self.assertAlmostEqual(5000.0, r["reaction_total_N"])

    def test_16_parse_missing_dat(self):
        r=parse_reaction_total(Path("does-not-exist.dat"))
        self.assertEqual(PARSE_REQUIRED, r["status"])

    def test_17_analytical_no_auto_approval(self):
        self.assertFalse(AN_SAFETY["automatic_professional_approval"])
        self.assertFalse(AN_SAFETY["automatic_code_compliance_claim"])

    def test_18_calculix_is_not_professional_review(self):
        self.assertFalse(CCX_SAFETY["second_solver_is_professional_review"])

    def test_19_raw_solver_evidence_required(self):
        self.assertTrue(CCX_SAFETY["raw_solver_evidence_required"])

    def test_20_release_locks_hard(self):
        self.assertEqual("LOCKED", AN_SAFETY["production_release"])
        self.assertEqual("LOCKED", AN_SAFETY["for_construction_release"])
        self.assertEqual("LOCKED", CCX_SAFETY["production_release"])
        self.assertEqual("LOCKED", CCX_SAFETY["for_construction_release"])

if __name__ == "__main__":
    unittest.main()
