import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "runners" / "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"
PROJECT_CONFIG = ROOT / "configs" / "projects" / "generic_building_structural_solver_input_analysis_v8_3_0.json"
ENGINE_CONFIG = ROOT / "configs" / "phoenix" / "structural" / "structural_solver_input_analysis_engine_v8_3_0.json"

spec = importlib.util.spec_from_file_location("phoenix_struct_solver_v8_3_0", RUNNER_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class TestStructuralSolverInputAnalysisV830(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
        cls.engine_cfg = json.loads(ENGINE_CONFIG.read_text(encoding="utf-8"))
        cls.package = module.build_solver_package(cls.payload)

    def test_engine_identity(self):
        self.assertEqual(self.package["engine"]["version"], "8.3.0")
        self.assertEqual(self.engine_cfg["version"], "8.3.0")

    def test_section_properties_are_derived_from_explicit_geometry(self):
        sections = self.package["solver_basis"]["derived_section_properties"]
        self.assertAlmostEqual(sections["SEC-COL"]["area_m2"], 0.09)
        self.assertAlmostEqual(sections["SEC-BEAM"]["area_m2"], 0.15)
        self.assertGreater(sections["SEC-BEAM"]["j_m4"], 0.0)

    def test_equivalent_nodal_loads_preserve_base_cases(self):
        loads = self.package["equivalent_nodal_loads_kN"]
        self.assertEqual(set(loads), {"LC-G", "LC-Q", "LC-WX"})
        self.assertAlmostEqual(loads["LC-Q"]["N0005"][2], -12.5)
        self.assertAlmostEqual(loads["LC-WX"]["N0001"][0], 1.5)
        self.assertAlmostEqual(loads["LC-WX"]["N0005"][0], 1.5)

    def test_self_weight_uses_explicit_density_geometry_and_gravity(self):
        trace = self.package["traceability"]["action_to_nodal_contributions"]["LA0001"]
        self.assertGreater(len(trace["contributions"]), 0)
        self.assertTrue(all(c["derivation"] == "EXPLICIT_DENSITY_GEOMETRY_SELF_WEIGHT" for c in trace["contributions"]))
        self.assertLess(self.package["equivalent_nodal_loads_kN"]["LC-G"]["N0005"][2], 0.0)

    def test_opensees_base_case_decks_generated(self):
        files = self.package["solver_files"]["opensees"]
        self.assertEqual(set(files), {"opensees_LC-G.tcl", "opensees_LC-Q.tcl", "opensees_LC-WX.tcl"})
        self.assertIn("element elasticBeamColumn", files["opensees_LC-G.tcl"])
        self.assertIn("element ShellMITC4", files["opensees_LC-G.tcl"])
        self.assertIn("analysis Static", files["opensees_LC-Q.tcl"])

    def test_calculix_base_case_decks_generated(self):
        files = self.package["solver_files"]["calculix"]
        self.assertEqual(set(files), {"calculix_LC-G.inp", "calculix_LC-Q.inp", "calculix_LC-WX.inp"})
        self.assertIn("*ELEMENT, TYPE=B31", files["calculix_LC-G.inp"])
        self.assertIn("*ELEMENT, TYPE=S4", files["calculix_LC-G.inp"])
        self.assertIn("*CLOAD", files["calculix_LC-Q.inp"])

    def test_load_combination_contract_preserved(self):
        self.assertEqual(self.package["summary"]["load_combination_count"], 2)
        self.assertEqual(self.package["combination_result_contract"]["method"], "LINEAR_SUPERPOSITION_OF_BASE_CASE_RESULTS")
        uls = next(c for c in self.package["load_combinations"] if c["id"] == "COMB-ULS-01")
        self.assertEqual([term["coefficient"] for term in uls["terms"]], [1.35, 1.5, 1.5])

    def test_solver_package_materialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = module.write_solver_package(self.package, Path(tmp))
            self.assertEqual(len(written), 7)
            self.assertTrue(Path(tmp, "opensees", "opensees_LC-G.tcl").exists())
            self.assertTrue(Path(tmp, "calculix", "calculix_LC-G.inp").exists())
            self.assertTrue(Path(tmp, "PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json").exists())

    def test_solver_execution_is_locked_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            module.write_solver_package(self.package, Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "locked by project"):
                module.execute_solver_package(self.payload, self.package, Path(tmp), allow_execution=True)

    def test_result_normalization_and_digital_twin_contract(self):
        raw = {"node_displacements": {"N0005": [0, 0, -0.001]}, "raw_solver_evidence_reference": "example.raw"}
        normalized = module.normalize_external_results("opensees", raw, self.package["solver_mapping"]["opensees"])
        self.assertEqual(normalized["approval_state"], "ANALYSIS_RESULT_CANDIDATE_ONLY")
        self.assertFalse(normalized["code_compliance_claimed"])
        self.assertTrue(self.package["digital_twin_writeback"]["enabled"])
        self.assertEqual(self.package["digital_twin_writeback"]["approval_state"], "CANDIDATE_ONLY")

    def test_release_safety(self):
        release = self.package["release"]
        self.assertFalse(release["automatic_structural_approval"])
        self.assertFalse(release["automatic_code_compliance_claim"])
        self.assertEqual(release["structural_model_release"], "LOCKED")
        self.assertTrue(release["engineering_review_required"])


if __name__ == "__main__":
    unittest.main()
