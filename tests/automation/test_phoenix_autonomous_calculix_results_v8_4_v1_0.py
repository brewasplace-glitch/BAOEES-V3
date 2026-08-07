from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from phoenix.autonomy.autonomous_calculix_results_v8_4 import (
    _instrument_deck,
    _section_force_components,
    _stress_envelope,
    _synthetic_dat,
    _synthetic_frd,
    autonomous_calculix_execution_enabled,
    detect_calculix_executable,
    parse_calculix_dat,
    parse_calculix_frd_last_stress,
)

class AutonomousCalculixV84Tests(unittest.TestCase):
    def test_01_test_mode_disables_live_solver_execution(self):
        with mock.patch.dict(os.environ, {"PHOENIX_TEST_MODE": "1"}, clear=False):
            self.assertFalse(autonomous_calculix_execution_enabled({"project_mode": "autonomous"}))

    def test_02_only_autonomous_session_enables_execution(self):
        with mock.patch.dict(os.environ, {"PHOENIX_TEST_MODE": "0"}, clear=False):
            self.assertTrue(autonomous_calculix_execution_enabled({"project_mode": "autonomous"}))
            self.assertFalse(autonomous_calculix_execution_enabled({"project_mode": "manual"}))
            self.assertFalse(autonomous_calculix_execution_enabled({"project_mode": "guided"}))

    def test_03_explicit_calculix_executable_has_precedence(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "ccx.exe"
            exe.write_bytes(b"x")
            with mock.patch.dict(os.environ, {"PHOENIX_CALCULIX_EXECUTABLE": str(exe)}, clear=False):
                found, info = detect_calculix_executable()
            self.assertEqual(found, exe.resolve())
            self.assertEqual(info["source"], "PHOENIX_CALCULIX_EXECUTABLE")

    def test_04_deck_instrumentation_adds_support_and_raw_output(self):
        deck = "*HEADING\n*NODE\n1,0,0,0\n*STEP\n*STATIC\n*END STEP\n"
        result = _instrument_deck(deck, support_tags=[1], element_ids=["M1", "S1"])
        self.assertIn("*NSET, NSET=PHX_SUPPORT_NODES", result)
        self.assertIn("*NODE PRINT, NSET=NALL", result)
        self.assertIn("*NODE PRINT, NSET=PHX_SUPPORT_NODES", result)
        self.assertIn("*EL PRINT, ELSET=E_M1", result)
        self.assertIn("*EL PRINT, ELSET=E_S1", result)
        self.assertIn("*EL FILE, SECTION FORCES", result)

    def test_05_dat_parser_reads_contract_shapes(self):
        p = parse_calculix_dat(_synthetic_dat())
        self.assertEqual(p["node_displacements"][2][0], 1.0e-6)
        self.assertEqual(p["support_total_forces"][1][0], -1.0)
        self.assertEqual(len(p["stresses_by_set"]["E_M1"]), 2)

    def test_06_frd_parser_reads_section_force_dataset(self):
        p = parse_calculix_frd_last_stress(_synthetic_frd())
        self.assertAlmostEqual(p[1]["SXX"], -99.996)
        self.assertAlmostEqual(p[1]["SZZ"], 4.12410e-09)
        self.assertIn("SXZ", p[1])
        comp = _section_force_components(p[1])
        self.assertEqual(set(comp), {"V1", "V2", "N", "T", "M2", "M1"})

    def test_07_real_calculix_fixed_width_frd_section_force_record(self):
        p = parse_calculix_frd_last_stress(_synthetic_frd())
        self.assertAlmostEqual(p[1]["SXX"], -99.996)
        self.assertIn("SXZ", p[1])
        self.assertNotIn("SZX", p[1])
        self.assertEqual(set(_section_force_components(p[1])), {"V1", "V2", "N", "T", "M2", "M1"})

    def test_08_stress_envelope_is_numeric_solver_data(self):
        env = _stress_envelope([[1,2,3,4,5,6],[-2,3,-4,5,-6,7]])
        self.assertEqual(env["SXX_MIN"], -2.0)
        self.assertEqual(env["SXX_MAX"], 1.0)
        self.assertEqual(env["SYZ_MAX_ABS"], 7.0)
        self.assertTrue(all(isinstance(v, float) for v in env.values()))

if __name__ == "__main__":
    unittest.main()
