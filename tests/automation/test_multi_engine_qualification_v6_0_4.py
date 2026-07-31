from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/phoenix/multi_engine_qualification_v6_0_0.json"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_multi_engine_qualification_v6_0_0.py"


class MultiEngineQualificationTests(unittest.TestCase):
    def test_config_has_six_engines(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            cfg["engines"],
            [
                "freecad",
                "ifcopenshell",
                "qgis",
                "calculix",
                "opensees",
                "energyplus",
            ],
        )
        self.assertEqual(
            cfg["production_release_policy"],
            "ALL_SIX_ENGINES_MUST_PASS",
        )
        self.assertFalse(cfg["simulated_results_allowed"])

    def test_runner_has_all_qualifiers(self):
        text = RUNNER.read_text(encoding="utf-8")
        for engine in (
            "freecad",
            "ifcopenshell",
            "qgis",
            "calculix",
            "opensees",
            "energyplus",
        ):
            self.assertIn(f'"{engine}"', text)
        self.assertIn("PRODUCTION RELEASE GATE: UNLOCKED", text)


class IfcOpenShellDedicatedRuntimeTests(unittest.TestCase):
    def test_ifcopenshell_runtime_routing_config(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        runtime = cfg["runtime_routing"]["ifcopenshell"]
        self.assertEqual(
            runtime["strategy"],
            "dedicated_python_with_import_probe",
        )
        self.assertEqual(
            runtime["environment_variable"],
            "IFCOPENSHELL_PYTHON",
        )

    def test_runner_uses_external_ifcopenshell_runtime(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("resolve_ifcopenshell_python", text)
        self.assertIn("IFCOPENSHELL_PYTHON", text)
        self.assertIn("qualification_ifcopenshell.py", text)
        self.assertIn(
            "REAL_IFC4_CREATE_WRITE_REOPEN_DEDICATED_RUNTIME",
            text,
        )


class CalculiXVerifiedAcceptanceReuseTests(unittest.TestCase):
    def test_calculix_verified_acceptance_reuse_config(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        contract = cfg["runtime_routing"]["calculix"]
        self.assertEqual(
            contract["strategy"],
            "invoke_installed_verified_acceptance_module",
        )
        self.assertEqual(contract["verified_contract_version"], "5.4.9")
        self.assertEqual(contract["solver"], "SPOOLES")
        self.assertEqual(
            contract["load_step_contract"],
            "CLOAD_WITHIN_STATIC_STEP",
        )
        self.assertEqual(contract["element_type"], "C3D8")
        self.assertIn(
            "calculix_acceptance_v5_4_9.py",
            contract["acceptance_module"],
        )

    def test_obsolete_inline_contract_is_removed(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        test_contract = cfg["test_contract"]["calculix"]
        self.assertEqual(
            test_contract["active_contract"],
            "VERIFIED_ACCEPTANCE_MODULE_REUSE_V5_4_9",
        )
        self.assertIn(
            "INLINE_DECK_REQUIRES_THREADS_KEY",
            test_contract["obsolete_contracts_removed"],
        )
        text = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("Phoenix C3D8 qualification", text)

    def test_runner_invokes_verified_calculix_acceptance(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("calculix_acceptance_v5_4_9.py", text)
        self.assertIn("calculix_engine_acceptance.json", text)
        self.assertIn("REAL_CCX_DAT_FRD_ARTIFACTS", text)
        self.assertIn("suite_acceptance_stdout.txt", text)
        self.assertIn("suite_acceptance_stderr.txt", text)
        self.assertIn('"linear_solver_contract": "SPOOLES"', text)
        self.assertIn(
            '"load_step_contract": "CLOAD_WITHIN_STATIC_STEP"',
            text,
        )

    def test_execution_marker_is_resolved_semantically(self):
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        resolved_strings = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                resolved_strings.add(node.value)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                try:
                    value = ast.literal_eval(node)
                except Exception:
                    continue
                if isinstance(value, str):
                    resolved_strings.add(value)

        expected = (
            "REUSED_VERIFIED_CALCULIX_V5_4_9_"
            "C3D8_SPOOLES_DAT_FRD_ACCEPTANCE"
        )
        self.assertIn(expected, resolved_strings)


if __name__ == "__main__":
    unittest.main()
