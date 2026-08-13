from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from phoenix.autonomy.scia_reference_model_beam_validation_v1_0 import (
    SOURCE_VALIDATED, SCIA_VALIDATED, SCIA_ANALYTICAL_VALIDATED,
    CROSS_VERIFIED, CALCULIX_PENDING, FAILED,
    parse_reference_xml, extract_scia_protocol, validate_sources,
    analytical, calculix_deck, run_calculix, SAFETY
)

class BeamReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path.cwd()
        cls.ref = cls.repo / "reference_models/structural/scia/beam_v1_0"

    def test_01_reference_source_files_exist(self):
        for name in ("Beam.esa","Beam.xml","Beam.xml.def","Beam_preview.jpg","reference_model_manifest.json"):
            self.assertTrue((self.ref/name).is_file(), name)

    def test_02_xml_exact_load_contract(self):
        x = parse_reference_xml(self.ref/"Beam.xml")
        self.assertEqual("Beam.xml.def", x["def_uri"])
        self.assertEqual("LF1", x["load_name"])
        self.assertEqual("B1", x["member"])
        self.assertEqual("LC1", x["load_case"])
        self.assertEqual("Z", x["direction"])
        self.assertEqual("Uniform", x["distribution"])
        self.assertEqual(-1000.0, x["value"])
        self.assertEqual(0.0, x["position_x1"])
        self.assertEqual(1.0, x["position_x2"])

    def test_03_existing_scia_protocol_exact_equilibrium(self):
        p = extract_scia_protocol(self.ref/"Beam.esa")
        self.assertEqual([-0.0, 0.0, -5.0], p["loads_kN"])
        self.assertEqual([0.0, 0.0, 5.0], p["reactions_in_nodes_kN"])

    def test_04_source_validation_passes(self):
        r = validate_sources(self.ref)
        self.assertEqual(SOURCE_VALIDATED, r["status"])

    def test_05_manifest_test_tolerances_not_general_engineering(self):
        m = json.loads((self.ref/"reference_model_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("SOFTWARE_REFERENCE_TEST_ONLY_NOT_GENERAL_ENGINEERING_TOLERANCE", m["benchmark_tolerances"]["scope"])
        self.assertTrue(m["safety"]["not_pat001_project_evidence"])

    def test_06_analytical_targets(self):
        s = {"status": SCIA_VALIDATED}
        r = analytical(self.ref, s)
        self.assertEqual(SCIA_ANALYTICAL_VALIDATED, r["status"])
        self.assertAlmostEqual(2500.0, r["reaction_each_N"])
        self.assertAlmostEqual(3125.0, r["max_sagging_moment_Nm"])

    def test_07_calculix_deck_has_100_beam_elements_and_5000N_total_load(self):
        with tempfile.TemporaryDirectory() as td:
            deck = calculix_deck(self.ref, Path(td), elements=100)
            text = deck.read_text(encoding="ascii")
            self.assertIn("*ELEMENT, TYPE=B31", text)
            self.assertIn("*NODE PRINT, NSET=SUPPORTS", text)
            loads = []
            active = False
            for line in text.splitlines():
                if line == "*CLOAD":
                    active = True
                    continue
                if active and line.startswith("*"):
                    break
                if active:
                    loads.append(float(line.split(",")[2]))
            self.assertAlmostEqual(-5000.0, sum(loads), places=6)

    @patch("phoenix.autonomy.scia_reference_model_beam_validation_v1_0.find_ccx")
    def test_08_missing_ccx_is_pending_not_fake_crossverified(self, find_mock):
        find_mock.return_value = None
        with tempfile.TemporaryDirectory() as td:
            r = run_calculix(self.ref, Path(td), None, 30)
            self.assertEqual(CALCULIX_PENDING, r["status"])

    def test_09_safety_boundaries(self):
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])
        self.assertFalse(SAFETY["reference_model_is_pat001_project_evidence"])
        self.assertFalse(SAFETY["benchmark_tolerances_are_general_engineering_tolerances"])
        self.assertEqual("LOCKED", SAFETY["production_release"])
        self.assertEqual("LOCKED", SAFETY["for_construction_release"])

if __name__ == "__main__":
    unittest.main()
